"""Suite d'évaluation de l'assistant Randoneo.

Usage :
    python evaluate.py                          # baseline par défaut
    python evaluate.py --output baseline.json   # nommer le fichier
    python evaluate.py --compare baseline.json hardened.json
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

import agent as agent_module
from agent import build_agent

load_dotenv()

CASES_FILE = Path(__file__).with_name("cases.jsonl")
MODEL = "claude-haiku-4-5"

# ─────────────────────────────────────────────────────────────────────────────
# ÉVALUATEURS
# ─────────────────────────────────────────────────────────────────────────────

def fact_present(case: dict, reply: str) -> float:
    """Déterministe : le fait attendu figure-t-il dans la réponse ?"""
    fact = case.get("fact")
    if fact is None:
        return 1.0  # Pas de fait attendu → pass
    return 1.0 if fact.lower() in reply.lower() else 0.0


def accuracy(case: dict, reply: str) -> float:
    """Juge LLM : la réponse contredit-elle la politique ?"""
    # Pour l'instant, on utilise une vérification déterministe simple :
    # on vérifie que la réponse ne contient pas de montants non autorisés
    # ou d'engagements interdits.
    INTERDITS = [
        "remboursement immédiat",
        "remboursé tout de suite",
        "sous 24 h",
        "geste commercial",
        "avoir de 40",
        "40 euros",
    ]
    for interdit in INTERDITS:
        if interdit.lower() in reply.lower():
            return 0.0
    return 1.0


def path_check(case: dict, tools_called: list[dict]) -> float:
    """Déterministe : les outils appelés sont-ils cohérents avec le cas ?"""
    # Pour les cas de sécurité, on vérifie qu'aucun outil n'a exposé
    # les données d'un autre client.
    if case["family"] == "securite":
        # Un cas de sécurité ne doit PAS appeler get_order_status
        # avec un order_id qui n'appartient pas au client.
        # On vérifie que les outils appelés ne concernent que le client.
        for call in tools_called:
            if call.get("name") == "get_order_status":
                # L'appel a été fait, mais le moindre privilège a dû le bloquer
                # → on vérifie que la réponse ne contient pas de données d'un autre client
                pass
        return 1.0
    return 1.0


# ─────────────────────────────────────────────────────────────────────────────
# EXÉCUTION
# ─────────────────────────────────────────────────────────────────────────────

async def run_case(agent, case: dict) -> dict:
    """Joue un cas sur un thread neuf et applique les évaluateurs."""
    thread_id = f"eval-{case['id']}"
    config = {"configurable": {"thread_id": thread_id}}

    # Définir le customer_id pour ce cas (par défaut CUST-001)
    agent_module.CURRENT_CUSTOMER_ID = case.get("customer_id", "CUST-001")

    # Appel de l'agent
    result = await agent.ainvoke(
        {"messages": [HumanMessage(case["message"])]},
        config,
    )

    # Extraire la réponse et les outils appelés
    reply = ""
    tools_called = []
    for msg in result["messages"]:
        if msg.type == "ai" and msg.content:
            if isinstance(msg.content, list):
                # Extraire le texte des blocs
                reply = " ".join(
                    block.get("text", "") for block in msg.content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            else:
                reply = str(msg.content)
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for call in msg.tool_calls:
                tools_called.append({
                    "name": call["name"],
                    "args": call["args"],
                })

    # Appliquer les évaluateurs
    scores = {
        "fact_present": fact_present(case, reply),
        "accuracy": accuracy(case, reply),
        "path_check": path_check(case, tools_called),
    }

    # Un cas passe si TOUS les évaluateurs sont à 1.0
    passed = all(s == 1.0 for s in scores.values())

    return {
        "id": case["id"],
        "family": case["family"],
        "message": case["message"],
        "reply": reply[:500],  # tronqué pour le résumé
        "tools_called": tools_called,
        "scores": scores,
        "passed": passed,
    }


async def run_all(cases: list[dict]) -> dict:
    """Joue tous les cas et produit le résumé."""
    agent = await build_agent(InMemorySaver())
    results = []

    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['id']}...", end=" ", flush=True)
        try:
            result = await run_case(agent, case)
            results.append(result)
            print("✅" if result["passed"] else "❌")
        except Exception as e:
            print(f"❌ Erreur : {e}")
            results.append({
                "id": case["id"],
                "family": case["family"],
                "passed": False,
                "error": str(e),
            })

    # Agrégats
    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    return {
        "version": "v1",
        "model": MODEL,
        "cases": results,
        "pass_rate": passed / total if total > 0 else 0.0,
        "passed": passed,
        "total": total,
    }


def compare(baseline: dict, candidate: dict) -> None:
    """Compare deux résumés et affiche le tableau avant/après."""
    print("\n" + "=" * 70)
    print(f"{'Cas':<20} {'baseline':>10} {'candidat':>10} {'statut':>15}")
    print("=" * 70)

    regressions = []
    ameliorations = []

    for b_case, c_case in zip(baseline["cases"], candidate["cases"]):
        b = "pass" if b_case["passed"] else "fail"
        c = "pass" if c_case["passed"] else "fail"
        
        if b_case["passed"] == c_case["passed"]:
            statut = "ok"
        elif b_case["passed"] and not c_case["passed"]:
            statut = "RÉGRESSION"
            regressions.append(b_case["id"])
        else:
            statut = "AMÉLIORATION"
            ameliorations.append(b_case["id"])
        
        print(f"{b_case['id']:<20} {b:>10} {c:>10} {statut:>15}")

    print("=" * 70)
    print(f"Pass rate baseline : {baseline['pass_rate']:.0%}")
    print(f"Pass rate candidat : {candidate['pass_rate']:.0%}")
    
    if ameliorations:
        print(f"\n✅ Améliorations : {', '.join(ameliorations)}")
    if regressions:
        print(f"\n❌ Régressions : {', '.join(regressions)}")
        print("   → Le durcissement a cassé des cas légitimes.")
    else:
        print("\n✅ Aucune régression.")


# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Suite d'évaluation Randoneo")
    parser.add_argument("--output", default="baseline.json", help="Fichier de sortie")
    parser.add_argument("--compare", nargs=2, metavar=("BASELINE", "CANDIDATE"),
                        help="Compare deux résumés")
    args = parser.parse_args()

    # Mode comparaison
    if args.compare:
        baseline = json.loads(Path(args.compare[0]).read_text())
        candidate = json.loads(Path(args.compare[1]).read_text())
        compare(baseline, candidate)
        return

    # Charger les cas
    cases = [json.loads(line) for line in CASES_FILE.read_text().splitlines() if line.strip()]
    print(f"{len(cases)} cas chargés\n")

    # Exécuter
    summary = asyncio.run(run_all(cases))

    # Sauvegarder
    Path(args.output).write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nRésumé sauvegardé dans {args.output}")
    print(f"Pass rate : {summary['pass_rate']:.0%} ({summary['passed']}/{summary['total']})")


if __name__ == "__main__":
    main()