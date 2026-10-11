# Outils

Génération des timelines des personnages, pas de 5 minutes par pas de 5 minutes.

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
- un événement n'existe pas dans le catalogue de la fiche ;
- l'anxiété au moment d'éteindre dépasse le seuil d'insomnie, alors que la journée le fait s'endormir en 15 minutes.

Les besoins passés sous leur seuil d'alerte sont listés dans le résumé de chaque journée.

## Ajouter une journée

1. Copier la journée précédente dans `outils/journees/<date>.py` et réécrire son contenu.
2. Lancer `python3 outils/generer_journee.py <date>`.
3. Corriger le contenu tant qu'une incohérence est signalée, et vérifier dans le résumé que les besoins sous le seuil d'alerte correspondent à ce que vit le personnage.
