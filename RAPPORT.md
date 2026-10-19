# Rapport — L'assistant Randoneo en production

*Complétez ce gabarit sans en changer la structure. Deux pages suffisent : chaque chiffre que vous écrivez ici doit sortir de la commande de la section « Rejouer les mesures ».*

**Auteur :**
**Date :**

## L'application

*Une phrase : ce que fait l'assistant, pour qui, et avec quelles capacités. Puis l'adresse à laquelle le correcteur la trouve, et le moyen d'y entrer.*

**En une phrase :**

**URL de l'application :**

**Accès :** *(mot de passe partagé, compte de démonstration, ou autre — indiquez ce qu'il faut saisir)*

**Dépôt du code :**

## Rejouer les mesures

*La commande exacte, copiable telle quelle, qui régénère le tableau de la section suivante. Indiquez ce qu'il faut installer et quelles variables d'environnement renseigner avant de la lancer.*

```bash
# installation

# variables d'environnement attendues

# la commande qui rejoue l'évaluation et compare les deux exécutions

```

**Durée approximative d'une exécution :**
**Coût approximatif d'une exécution :**

## Évaluation avant et après durcissement

*Le tableau ci-dessous se remplit avec la sortie de la commande. Une ligne par cas, ou une ligne par famille si votre jeu est large — dites lequel des deux vous présentez. L'écart est signé : un nombre négatif est une régression.*

**Granularité présentée :** *(par cas / par famille)*

| Cas ou famille | Score avant | Score après | Écart |
| --- | --- | --- | --- |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |

**Synthèse.**

| Indicateur | Avant | Après | Écart |
| --- | --- | --- | --- |
| Taux de réussite |  |  |  |
| Nombre de cas cassés |  |  |  |
| Nombre de cas du jeu |  |  |  |

*Deux ou trois phrases : quel cas bouge, dans quel sens, et pourquoi. Si un cas légitime a régressé, dites ce que vous en avez fait.*

## Attaques menées

*Une ligne par attaque, y compris celles qui ne passaient déjà pas. Précisez pour chacune ce qu'elle visait — ce que l'assistant **dit**, ou ce qu'il **fait**. La dernière colonne nomme la couche qui arrête l'attaque, et une seule : celle qui la bloquerait encore si les autres tombaient.*

| Attaque | Cible (dire / faire) | Ce qu'elle obtenait avant | Ce qu'elle obtient après | Couche qui l'arrête |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |

*Deux ou trois phrases : quelle attaque a été la plus difficile à faire aboutir, et laquelle serait la plus difficile à refermer durablement.*

## Défense d'architecture

*Trois questions, trois réponses courtes. On attend un raisonnement, pas une description de ce que vous avez écrit.*

**Pourquoi ces garde-fous, dans cet ordre ?** *(ce que chaque couche garantit, ce qu'elle ne fait que rendre moins probable, et ce que vous avez décidé de ne pas protéger)*

**Quel contrôle a bloqué une réponse honnête, et qu'en avez-vous fait ?** *(le cas légitime que votre durcissement a cassé, l'arbitrage retenu — préciser la référence, desserrer, sortir la règle du prompt — et ce que cet arbitrage laisse passer en échange)*

**Pourquoi cette cible d'hébergement ?** *(ce qui l'a fait choisir, ce qu'elle ne donne pas, et ce que devient votre conteneur)*

**Que feriez-vous différemment pour un vrai service ?** *(persistance, identité des utilisateurs, supervision, coûts, isolation des données — citez ce qui changerait en premier et pourquoi)*

## Limites connues

*Section honnête, et notée comme telle. Ce qui n'a pas été traité, ce qui n'a pas été mesuré, ce qui casserait sous une charge réelle. Un manque annoncé se corrige ; un manque caché se découvre en production.*

-
-
-
