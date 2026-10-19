# Base de départ — l'assistant Randoneo à industrialiser

Cette archive contient un assistant de support **fonctionnel** : un agent ReAct dont toutes
les capacités vivent dans un serveur MCP, une mémoire persistante par conversation, et une
validation humaine sur l'action sensible. C'est le point de départ du projet, pour ceux qui
n'ont pas de rendu fonctionnel du projet précédent ou qui préfèrent repartir d'une base saine.

Elle ne contient **aucune** des quatre couches que le projet demande d'ajouter : pas de suite
d'évaluation, pas de garde-fou, pas d'interface, pas de déploiement. C'est ce qui reste à
faire, et c'est ce qui est noté.

## Installation

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # puis renseignez vos deux clés
set -a && . ./.env && set +a
```

| Variable | À quoi elle sert |
| --- | --- |
| `ANTHROPIC_API_KEY` | Le modèle de l'agent |
| `OPENAI_API_KEY` | Les embeddings de la base de connaissances, appelés par le serveur d'outils |

Python 3.11 au minimum : en 3.10, la configuration d'exécution ne traverse pas les appels
asynchrones et la validation humaine échoue sur `Called get_config outside of a runnable context`.

## Vérifier que la base tourne

Cinq minutes ici vous éviteront de confondre plus tard une panne d'origine avec un effet de
votre durcissement.

```bash
python randoneo_support.py    # le serveur seul : il doit démarrer et attendre
python demo.py                # les scénarios de vérification, dont une escalade
python chat.py                # conversation interactive (fil « client-1 »)
python chat.py client-2       # une autre conversation, isolée de la première
```

La conversation est persistée dans `randoneo_memory.sqlite` : relancez `chat.py` avec le même
identifiant de fil, l'assistant reprend là où vous en étiez.

## Ce que contient la base

| Fichier | Ce qu'il porte |
| --- | --- |
| `randoneo_support.py` | Le serveur MCP : catalogue, documentation, suivi de commande, ouverture de ticket |
| `agent.py` | L'agent : découverte des capacités, prompt système, point d'arrêt humain sur `create_ticket` |
| `chat.py` | Une boucle de conversation en ligne de commande, avec streaming et reprise après validation |
| `demo.py` | Les scénarios de vérification de la base |
| `data/` | Le catalogue produit, le corpus documentaire et les commandes |

Deux points de ce métier comptent pour la suite du projet, et ce sont eux qu'on attaque.

**Une règle interne confidentielle.** Le prompt système de `agent.py` porte la politique de
geste commercial de Randoneo : un avoir plafonné, sous condition, que l'assistant ne doit ni
révéler ni proposer de lui-même. C'est une règle de l'entreprise au même titre que le délai
de retour — et c'est ce qu'un attaquant cherchera à faire sortir.

**Un transporteur.** Randoneo sous-traite la livraison : le suivi d'un colis se consulte chez
le transporteur, dont le lien part dans les réponses aux clients. Ce lien est légitime, il
n'appartient pourtant pas à l'entreprise.

## Si vous partez de votre propre rendu

Gardez votre code : c'est le vôtre, avec ses choix, et un durcissement se mesure mieux sur un
objet qu'on connaît. Reprenez seulement les deux éléments ci-dessus, sans lesquels une partie
du projet n'aurait pas d'objet :

1. le bloc `INTERNAL_RULES` de `agent.py`, ajouté à votre prompt système ;
2. le dossier `data/` de cette archive, dont la documentation mentionne le transporteur — et
   le `tracking_url` que `get_order_status` construit dans `randoneo_support.py`.

Rien d'autre n'est à reprendre.

## Ce que la base ne fait pas

Elle répond juste sans que personne n'en ait la preuve, elle obéit à qui sait lui parler, elle
ne s'atteint que depuis votre terminal et elle s'arrête quand vous le fermez. C'est exactement
le sujet du projet.
