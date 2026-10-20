"""Serveur MCP du support Randoneo : les capacités métier de l'assistant.

Quatre tools et une resource. Aucun agent ici : ce serveur ne sait pas qui l'appelle.
Lancement direct (stdio) : python randoneo_support.py
En HTTP : mcp.run(transport="http", host="127.0.0.1", port=8000)
"""
import json
import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from fastmcp import FastMCP

mcp = FastMCP("randoneo-support")

DATA = Path(__file__).with_name("data")
CATALOG = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
ORDERS = json.loads((DATA / "orders.json").read_text(encoding="utf-8"))
CORPUS = json.loads((DATA / "randoneo_corpus.json").read_text(encoding="utf-8"))
TICKETS = []

# Identité du client courant (définie par l'application avant chaque appel)
CURRENT_CUSTOMER_ID = "CUST-001"  # valeur par défaut pour les tests



# Le transporteur choisi par Randoneo : le suivi d'un colis se consulte chez lui.
TRACKING_URL = "https://suivi.colisdirect.fr/{}"

# La base de connaissances du cours 02, réduite à sa fonction d'outil.
_embed = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.environ["OPENAI_API_KEY"], model_name="text-embedding-3-small",
)
_kb = chromadb.Client().create_collection(
    name="randoneo_kb", embedding_function=_embed, metadata={"hnsw:space": "cosine"},
)
_kb.add(ids=list(CORPUS), documents=[entry["text"] for entry in CORPUS.values()])


@mcp.tool
def search_catalog(query: str, category: str | None = None) -> list[dict]:
    """Recherche des produits au catalogue Randoneo par mots-clés (nom, description, catégorie) ou par SKU.

    query : mots-clés du client, par ex. « tente légère 2 places », ou un SKU exact.
    category : catégorie à laquelle restreindre la recherche (Tentes, Sacs, Chaussures…).
    À utiliser dès qu'un client demande un prix, une disponibilité ou un conseil d'achat.
    Renvoie une liste de produits {sku, name, price_eur, stock}.
    """
    terms = [term for term in query.lower().split() if len(term) > 2]
    found = []
    for item in CATALOG:
        if category and item["category"].lower() != category.strip().lower():
            continue
        # Recherche par SKU exact (priorité maximale)
        if item["sku"].lower() == query.strip().lower():
            found.append((999, {champ: item[champ] for champ in ("sku", "name", "price_eur", "stock")}))
            continue
        # Recherche par mots-clés
        haystack = f"{item['name']} {item['description']} {item['category']}".lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            found.append((score, {champ: item[champ] for champ in ("sku", "name", "price_eur", "stock")}))
    found.sort(key=lambda pair: -pair[0])
    return [product for _, product in found[:5]]

@mcp.tool
def get_order_status(order_id: str, customer_id: str) -> dict:
    """Donne l'état d'une commande Randoneo à partir de son identifiant.

    order_id : identifiant de commande, par ex. « RND-10234 ».
    customer_id : identifiant du client connecté (fourni par l'application, jamais par le modèle).
    À utiliser dès qu'un client demande où en est sa commande, ou parle d'un colis.
    """
    for order in ORDERS:
        if order["order_id"].upper() == order_id.strip().upper():
            # Moindre privilège : vérifier que la commande appartient au client
            if order.get("customer_id") != customer_id:
                return {"erreur": "Commande introuvable. Vérifiez le numéro."}
            # Ne renvoyer que les champs utiles (pas d'adresse, pas de moyen de paiement)
            fiche = {
                "order_id": order["order_id"],
                "status": order["status"],
                "tracking_number": order["tracking_number"],
                "tracking_url": TRACKING_URL.format(order["tracking_number"]) if order["tracking_number"] else None,
                "eta": order["eta"],
                "total_eur": order["total_eur"],
                "items": order["items"],
            }
            return fiche
    return {"erreur": f"Commande « {order_id} » introuvable. Vérifiez le format RND-XXXXX."}


@mcp.tool
def search_knowledge_base(query: str) -> list[str]:
    """Cherche dans la documentation Randoneo : politiques de retour, remboursement,
    livraison, paiement, garantie, fidélité, RGPD, et fiches produit.

    query : la question du client, ou les mots-clés à rechercher.
    À utiliser dès que la réponse relève d'une règle de l'entreprise plutôt que d'une donnée client.
    """
    result = _kb.query(query_texts=[query], n_results=3)
    return result["documents"][0]


# Liste fermée des intents autorisés (nomenclature de l'entreprise)
ALLOWED_INTENTS = {
    "return_refund",
    "payment_issue",
    "order_tracking",
    "product_question",
    "product_advice",
    "account",
    "other",
}

@mcp.tool
def create_ticket(intent: str, summary: str, order_id: str | None = None) -> str:
    """Ouvre un ticket au support Randoneo pour escalader une demande vers un humain.

    intent : nature de la demande (return_refund, payment_issue, order_tracking, product_question…).
    summary : résumé de la demande du client, en une phrase.
    order_id : identifiant de la commande concernée, si le client en mentionne une.
    Action sensible : l'agent la soumet à validation avant de l'exécuter.
    """
    # Moindre privilège : borner l'intent à la nomenclature
    if intent not in ALLOWED_INTENTS:
        return f"Erreur : l'intent '{intent}' n'est pas autorisé. Utilisez : {', '.join(sorted(ALLOWED_INTENTS))}."
    
    # Moindre privilège : borner la longueur du résumé
    if len(summary) > 200:
        summary = summary[:200] + "..."
    
    # Moindre privilège : vérifier que la commande appartient au client
    if order_id:
        for order in ORDERS:
            if order["order_id"].upper() == order_id.strip().upper():
                if order.get("customer_id") != CURRENT_CUSTOMER_ID:
                    return "Erreur : commande introuvable. Vérifiez le numéro."
                break
        else:
            return "Erreur : commande introuvable. Vérifiez le numéro."
    
    TICKETS.append({"intent": intent, "summary": summary, "order_id": order_id})
    return f"Ticket TICK-{len(TICKETS):03d} ouvert ({intent})."



@mcp.resource("randoneo://product/{sku}")
def product_sheet(sku: str) -> str:
    """Fiche détaillée d'un produit Randoneo, au format Markdown."""
    for item in CATALOG:
        if item["sku"].upper() == sku.strip().upper():
            lignes = [
                f"# {item['name']} ({item['sku']})",
                f"- Catégorie : {item['category']}",
                f"- Prix : {item['price_eur']} €",
                f"- Stock : {item['stock']}",
                "",
                item["description"],
            ]
            attributs = item.get("attributes") or {}
            if attributs:
                lignes += ["", "## Caractéristiques"]
                lignes += [f"- {cle} : {valeur}" for cle, valeur in attributs.items()]
            return "\n".join(lignes)
    return f"# Produit {sku} introuvable"


if __name__ == "__main__":
    mcp.run()  # stdio : l'hôte lance ce fichier en sous-processus
