"""Rejoue les scénarios de vérification de la base, sans interaction.

Usage : python demo.py
Chaque scénario affiche les outils appelés, puis la réponse de l'assistant.
"""
import asyncio

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from agent import build_agent

DB_DEMO = "demo_memory.sqlite"


def outils_appeles(messages):
    return [appel["name"] for message in messages
            for appel in (getattr(message, "tool_calls", None) or [])]


async def scenario(agent, titre, question, config, decision=None):
    print(f"\n{'=' * 78}\n{titre}\n  « {question} »")
    resultat = await agent.ainvoke({"messages": [HumanMessage(question)]}, config)

    if "__interrupt__" in resultat:
        print(f"  [interruption] {resultat['__interrupt__'][0].value}")
        print(f"  [décision de l'opérateur] {decision}")
        resultat = await agent.ainvoke(Command(resume=decision), config)

    print("  outils :", outils_appeles(resultat["messages"]) or "aucun")
    print("  réponse :", resultat["messages"][-1].content.replace("\n", " ")[:220])


async def main():
    async with AsyncSqliteSaver.from_conn_string(DB_DEMO) as checkpointer:
        agent = await build_agent(checkpointer)

        await scenario(agent, "1. Une règle de l'entreprise → base de connaissances",
                       "J'ai combien de temps pour retourner un article ?",
                       {"configurable": {"thread_id": "demo-1"}})

        await scenario(agent, "2. Une donnée client → suivi de commande",
                       "Où en est ma commande RND-10234 ?",
                       {"configurable": {"thread_id": "demo-2"}})

        await scenario(agent, "3. Deux outils dans le même tour",
                       "Où en est ma commande RND-10238, et sous quel délai serai-je remboursé "
                       "une fois le colis renvoyé ?",
                       {"configurable": {"thread_id": "demo-3"}})

        await scenario(agent, "4. Action sensible approuvée",
                       "Ma tente de la commande RND-10238 est arrivée déchirée, je veux un remplacement.",
                       {"configurable": {"thread_id": "demo-4"}}, decision="approve")

        await scenario(agent, "5. Action sensible refusée",
                       "Mon colis de la commande RND-10241 n'est jamais arrivé, alors qu'il est "
                       "marqué expédié. Je veux un dédommagement.",
                       {"configurable": {"thread_id": "demo-5"}}, decision="reject")

        # 6. La mémoire : question de suivi sur le thread du scénario 2.
        suite = {"configurable": {"thread_id": "demo-2"}}
        print(f"\n{'=' * 78}\n6. Mémoire de conversation (même thread que le scénario 2)\n"
              "  « Et elle arrive quand ? »")
        resultat = await agent.ainvoke({"messages": [HumanMessage("Et elle arrive quand ?")]}, suite)
        print("  outils :", outils_appeles(resultat["messages"][-2:]) or "aucun (répond de mémoire)")
        print("  réponse :", resultat["messages"][-1].content.replace("\n", " ")[:220])


if __name__ == "__main__":
    asyncio.run(main())
