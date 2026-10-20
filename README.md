# Assistant Randoneo — Industrialisation

Ce projet est l'aboutissement du fil rouge Randoneo. Il part d'un assistant de support fonctionnel (agent ReAct + serveur MCP + mémoire + validation humaine) et y ajoute les **quatre couches d'industrialisation** demandées :

1. Une suite d'évaluation (baseline vs hardened).
2. Des garde-fous (défense en profondeur).
3. Une interface Streamlit (authentification, streaming, validation).
4. Un déploiement en ligne (URL publique).

---

## 🌐 Application en ligne

**URL de l'application :** [https://randoneo-assistant-hocine.streamlit.app/](https://randoneo-assistant-hocine.streamlit.app/)

**Accès :** L'application est protégée par un mot de passe. Pour l'obtenir, contactez l'auteur ou consultez le rapport de projet `RAPPORT.md`.

Si vous clonez ce dépôt pour tester en local, vous pouvez définir votre propre mot de passe dans `.streamlit/secrets.toml` (voir la section Installation).

**Dépôt du code :** [https://github.com/hocine-drioueche/projet_production](https://github.com/hocine-drioueche/projet_production)

---

## 📦 Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Puis renseignez vos deux clés API.

set -a && . ./.env && set +a

# Pour l'interface locale, créez aussi le fichier de secrets Streamlit :
mkdir -p .streamlit
echo 'app_password = "votre_mot_de_passe_local"' > .streamlit/secrets.toml
```

### Variables de configuration

| **Variable** | **À quoi elle sert** |
| :--- | :--- |
| `ANTHROPIC_API_KEY` | Le modèle de l'agent. |
| `OPENAI_API_KEY` | Les embeddings de la base de connaissances, appelés par le serveur d'outils. |
| `app_password` | Le mot de passe d'accès à l'interface Streamlit, défini dans `.streamlit/secrets.toml`. |

**Version de Python :** Python 3.11 au minimum. En Python 3.10, la configuration d'exécution ne traverse pas les appels asynchrones et la validation humaine échoue.

---

## 🏗️ Architecture du projet

| **Fichier** | **Ce qu'il porte** |
| :--- | :--- |
| `randoneo_support.py` | **Le serveur MCP :** catalogue, documentation, suivi de commande (durci), ouverture de ticket (durci). |
| `agent.py` | **L'agent :** découverte des capacités, prompt système, point d'arrêt humain, injection du `customer_id`. |
| `app.py` | **L'interface Streamlit :** authentification, streaming, étapes, validation humaine, fil dérivé de l'identité. |
| `cases.jsonl` | **Le jeu de cas d'évaluation :** 15 cas répartis sur les 4 familles (nominal, piège, limite, sécurité). |
| `evaluate.py` | **La suite d'évaluation :** évaluateurs, exécution, résumé, comparaison baseline/candidat. |
| `attacks.py` | **Les 4 charges d'attaque** et leurs marqueurs, rejouables. |
| `baseline.json` | Le résumé de l'évaluation **avant** durcissement (87 %). |
| `hardened.json` | Le résumé de l'évaluation **après** durcissement (100 %). |
| `attacks.json` | Le résumé des attaques **après** durcissement (0/4). |
| `data/` | Le catalogue produit, le corpus documentaire et les commandes. |
| `Dockerfile` | L'image de conteneur (application + serveur MCP) : utilisateur non-root (appuser, uid    1000), HEALTHCHECK, exposition sur 0.0.0.0:7860. |
| `RAPPORT.md` | Le rapport de projet (2 pages). |

---

### 🐳 Le conteneur, et pourquoi il existe

L'application est conteneurisable : le `Dockerfile` installe les dépendances, copie le code, crée un utilisateur non-root (`appuser`, uid 1000) et démarre Streamlit sur `0.0.0.0:7860`. Un `HEALTHCHECK` vérifie que l'application répond, et le `.dockerignore` exclut les secrets (`.env`, `.streamlit/`), les environnements virtuels et la documentation.

**Streamlit Community Cloud n'exécute pas cette image** — il clone le dépôt et installe depuis `requirements.txt`. Le conteneur reste néanmoins ce qui rend l'application portable vers un autre hébergeur (Cloud Run, App Runner, Container Apps…) : le déménagement coûte un `docker push`.




## 🚀 Vérifier que la base fonctionne (avant durcissement)

```bash
# Le serveur seul : il doit démarrer et attendre
python randoneo_support.py

# Les scénarios de vérification, dont une escalade
python demo.py

# Conversation interactive (fil « client-1 »)
python chat.py

# Une autre conversation, isolée de la première
python chat.py client-2
```

La conversation est persistée dans `randoneo_memory.sqlite` : relancez `chat.py` avec le même identifiant de fil pour que l'assistant reprenne là où vous en étiez.

---

## 🖥️ Lancer l'interface Streamlit

```bash
streamlit run app.py
```

L'application s'ouvre sur [http://localhost:8501](http://localhost:8501).

Le mot de passe d'accès est celui que vous avez défini dans `.streamlit/secrets.toml`.

---

## 🧪 Rejouer les mesures

```bash
# 1. Activer l'environnement virtuel
source .venv/bin/activate

# 2. Charger les variables d'environnement
set -a && source .env && set +a

# 3. Lancer la baseline (assistant avant durcissement)
python evaluate.py --output baseline.json

# 4. Lancer le candidat (assistant durci)
python evaluate.py --output hardened.json

# 5. Comparer les résultats
python evaluate.py --compare baseline.json hardened.json
```

**Résultat attendu :** un tableau comparatif avant/après avec le taux de réussite (*pass rate*).

---

## 🛡️ Les garde-fous : ce qui a été ajouté

Le projet applique **trois couches de défense en profondeur**.

### 1. Moindre privilège (garantie)

- `get_order_status` reçoit `customer_id` depuis la session (via `agent.py`), et non depuis le modèle. Il filtre également les champs renvoyés (pas d'adresse ni de moyen de paiement).
- `create_ticket` limite les intentions à une liste fermée (`ALLOWED_INTENTS`) et limite la longueur du résumé.
- `search_catalog` permet également la recherche par SKU.

### 2. Validation de sortie (rattrapage)

- Contrôle déterministe des références inventées (adresses e-mail et URL hors des domaines Randoneo).
- Juge LLM binaire pour détecter les promesses non conformes à la politique.

### 3. Délimitation (réduction de la probabilité)

- Le contenu non fiable est encadré par des balises comportant un identifiant aléatoire.

---

## 📊 Les chiffres du projet

| **Indicateur** | **Avant durcissement** | **Après durcissement** |
| :--- | :--- | :--- |
| **Taux de réussite (*pass rate*)** | 87 % (13/15) | **100 % (15/15)** |
| **Attaques réussies** | 1/4 | **0/4** |

### Détail des corrections

- `limite_04` : `search_catalog` ne recherchait pas par SKU → **corrigé**.
- `securite_01` : `get_order_status` ne vérifiait pas `customer_id` → **corrigé**.
- `contournement` : l'agent accordait un avoir de 40 € → **corrigé** grâce aux restrictions de `create_ticket`.

---

## ⚠️ Points d'attention et limites connues

- **La mémoire de conversation n'est pas persistante :** avec `InMemorySaver`, elle est perdue au redémarrage de l'application.
- **Le mot de passe est partagé :** il n'existe pas d'identité individuelle. Pour aller plus loin, une authentification OIDC avec `st.login()` serait nécessaire.
- **L'injection indirecte n'est pas complètement neutralisée :** la délimitation réduit la probabilité de réussite, mais un document bien rédigé peut encore contourner les instructions.
- **Le coût n'est pas mesuré en production :** aucun système de traçage (*tracing*) n'est encore connecté (LangSmith ou Langfuse).

---

## 📄 Licence

Projet pédagogique — fil rouge du module **Industrialisation IA**.

---

## 👤 Auteur

**Hocine Drioueche**

- GitHub : [@hocine-drioueche](https://github.com/hocine-drioueche)
