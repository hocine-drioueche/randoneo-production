"""Boucle de chat de l'assistant Randoneo : streaming, mémoire, validation humaine.

Usage : python chat.py [thread_id]
La conversation est persistée sous ce thread_id : relancez le script avec le même
identifiant et l'assistant reprend là où vous en étiez.
"""
import asyncio
import sys

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from agent import DB, build_agent


async def diffuser(agent, entree, config):
    """Diffuse les étapes et les tokens au fil de l'eau.

    Renvoie `(nb_morceaux_de_texte, interruption)`. Deux subtilités valent le détour :
    le flux `updates` porte l'interruption sous la clé `__interrupt__` — et non sous un
    nom de nœud —, et à la reprise LangGraph ne rediffuse aucun token. D'où le compteur,
    qui dit à l'appelant s'il doit lire la réponse dans l'état sauvegardé.
    """
    tokens, interruption = 0, None
    async for mode, data in agent.astream(entree, config, stream_mode=["updates", "messages"]):
        if mode == "updates":
            for cle, maj in data.items():
                if cle == "__interrupt__":
                    interruption = maj[0].value
                    continue
                if not isinstance(maj, dict):
                    continue
                message = (maj.get("messages") or [None])[-1]
                for appel in getattr(message, "tool_calls", None) or []:
                    print(f"  · {appel['name']}({appel['args']})")
        elif mode == "messages":
            chunk, _ = data
            if chunk.type == "AIMessageChunk" and chunk.text:
                print(chunk.text, end="", flush=True)
                tokens += 1
    print()
    return tokens, interruption


async def repondre(agent, entree, config):
    """Fait parler l'agent, en traitant les validations humaines jusqu'à la réponse finale."""
    tokens, interruption = await diffuser(agent, entree, config)

    while interruption:
        print(f"[validation requise] {interruption}")
        try:
            reponse = input("approuver ? (o/n) > ").strip().lower()
        except EOFError:
            reponse = "n"
        decision = "approve" if reponse.startswith("o") else "reject"

        print("assistant > ", end="")
        tokens, interruption = await diffuser(agent, Command(resume=decision), config)
        if not tokens:
            etat = await agent.aget_state(config)
            print(etat.values["messages"][-1].content)


async def main():
    thread_id = sys.argv[1] if len(sys.argv) > 1 else "client-1"
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncSqliteSaver.from_conn_string(DB) as checkpointer:
        agent = await build_agent(checkpointer)
        print(f"Assistant Randoneo — conversation « {thread_id} ». Ctrl-D pour quitter.\n")

        while True:
            try:
                question = input("vous > ").strip()
            except EOFError:
                print("\nÀ bientôt.")
                return
            if not question:
                continue

            print("assistant > ", end="")
            await repondre(agent, {"messages": [HumanMessage(question)]}, config)


if __name__ == "__main__":
    asyncio.run(main())
