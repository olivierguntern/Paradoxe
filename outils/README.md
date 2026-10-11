# Outils

Génération des timelines des personnages, pas de 5 minutes par pas de 5 minutes.

Deux façons de produire une journée :
- **rédigée à la main** (`journees/<date>.py`), puis calculée par le moteur : c'est ainsi qu'ont été écrits les jours de référence ;
- **vécue par l'agent autonome** (`agent.py`), qui décide seul de chaque pas à partir de ses recettes et de ses règles.

## Principe

| Ce qui est rédigé à la main (`journees/<date>.py`) | Ce qui est calculé (`moteur.py`) |
|---|---|
| Actions, pensées, rêves | Déplacements : chemin le plus court sur le plan, distance, durée, foulées |
| Événements vécus (catalogue de la fiche) | Lumière : interrupteurs selon les pièces sans fenêtre et le coucher du soleil |
| Objets déplacés, appareils utilisés | Besoins à chaque pas (taux de la fiche) |
| Provisions consommées | Émotions, uniquement à partir des événements, des besoins et du retour à l'état de base |
| Escaliers et parcours extérieurs | Concentration selon l'activité, la fatigue et les émotions |

Chaque journée part de l'**état exact de la fin de la veille** (besoins, émotions, pièce, lumières, appareils, position de chaque objet). Le premier jour part de la fiche.

## Commandes

```bash
# Vérifier la fiche du personnage
python3 outils/verifier_fiche.py data/personnages/thomas-berthier.json

# Générer une journée (la veille doit déjà être générée)
python3 outils/generer_journee.py 2010-03-08
python3 outils/generer_journee.py 2010-03-09
```

Chaque génération écrit `data/timelines/<personnage>/<date>.json` (données complètes) et `<date>.md` (version lisible).

## Contrôles de cohérence

La génération s'arrête avec un message « Incohérence » si :
- une journée ne compte pas exactement 288 pas, ou si deux activités se chevauchent ou laissent un trou ;
- un objet est déplacé depuis un endroit où il ne se trouve pas (sa position est suivie d'un jour à l'autre) ;
- un événement ou un produit n'existe pas dans la fiche ;
- une provision est consommée alors qu'il n'en reste pas assez (le stock est suivi d'un jour à l'autre) ;
- la durée d'endormissement prévue par la journée ne correspond pas à l'état émotionnel au moment d'éteindre (45 minutes si l'anxiété ou l'excitation dépasse son seuil, 15 sinon).

Les besoins passés sous leur seuil d'alerte sont listés dans le résumé de chaque journée.

## Ajouter une journée

1. Copier la journée précédente dans `outils/journees/<date>.py` et réécrire son contenu.
2. Lancer `python3 outils/generer_journee.py <date>`.
3. Corriger le contenu tant qu'une incohérence est signalée, et vérifier dans le résumé que les besoins sous le seuil d'alerte correspondent à ce que vit le personnage.

## Agent autonome

L'agent suit le plan de sa journée et ses routines, mais décide chaque pas selon son état, lu dans la simulation : besoins, émotions, objets, provisions, avancement des travaux. Ses connaissances sont des données, dans `data/agents/<personnage>/` :

| Fichier | Contenu |
|---|---|
| `regles.json` | Plan de la journée : réveil, jours de course, matins, plages d'atelier, soirées particulières |
| `blocs.json` | Recettes d'activités (lever, douche, course, pauses, lessive, match…) extraites des journées de référence |
| `travaux.json` | Opérations de chaque réparation, ordre de priorité, cycles de machine, observations de 24 h, validations |
| `seances.json` | Séances du soir sur la montre du grand-père, opérations obligatoires et facultatives, seuil de fatigue |
| `repas.json` | Recettes des repas de chaque jour, avec les cuissons longues à lancer en avance |
| `pensees.json` | Modèles de pensées, préoccupations, carnet du soir et rêves |

```bash
# Faire vivre la semaine par l'agent, à partir de la fiche
python3 outils/simuler_agent.py 2010-03-08 2010-03-10 --dossier data/simulations/thomas-berthier

# Comparer une journée de l'agent à la journée de référence
python3 outils/comparer_journees.py data/timelines/thomas-berthier/2010-03-09.json data/simulations/thomas-berthier/2010-03-09.json

# Prolonger la semaine officielle : état physique de la référence, mémoire de l'agent simulé
python3 outils/simuler_agent.py 2010-03-11 2010-03-11 --dossier data/timelines/thomas-berthier --memoire data/simulations/thomas-berthier
```

Le résultat de la validation est dans `data/simulations/thomas-berthier/VALIDATION.md`.
