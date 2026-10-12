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

```bash
# Vivre la fin de semaine (vendredi à dimanche) à la suite du jeudi
python3 outils/simuler_agent.py 2010-03-12 2010-03-14 --dossier data/timelines/thomas-berthier
```

Le résultat de la validation est dans `data/simulations/thomas-berthier/VALIDATION.md`.

### Interruptions par les besoins

Pendant l'atelier, une séance, la lecture, la musique, le temps libre ou la grasse matinée, l'agent vérifie ses besoins à chaque pas. Si l'un d'eux passe sous son seuil d'alerte (fiche, section `besoins`), il s'interrompt un pas, puis reprend son activité :

| Besoin | Seuil | Réponse |
|---|---|---|
| Toilettes | 25 | Passe aux toilettes |
| Soif | 40 | Boit un grand verre d'eau à la cuisine |
| Faim | 35 | Mange un fruit ou deux biscottes, selon le stock ; pas dans les 45 minutes qui précèdent un repas |

Il ne s'interrompt pas si l'activité se termine dans les 10 minutes. Chaque interruption figure dans les « écarts à la routine » du résumé de la journée.

Avant une séance sur la montre du grand-père, il anticipe : si les toilettes ou la soif passeraient sous leur seuil avant la fin prévue de la séance, il y répond en allant s'installer (`regles.json`, section `anticipation_seance`).

### Livres

Les livres à lire sont listés dans `regles.json` (section `lecture.livres`), dans l'ordre : objet de la fiche, titre, nombre de pages, page de départ, pensées de début et de fin. Il lit 5 pages par pas. Quand un livre est fini, il le range dans la bibliothèque du séjour à la séance de lecture suivante et prend le suivant. Le reste d'une plage de lecture, une fois le livre fini, devient de la musique.

### Fin de semaine

Le samedi et le dimanche n'ont pas de sonnerie : réveil naturel entre 07:30 et 08:30. Le plan de ces journées (ménage, sieste, sortie longue du dimanche, séances sur la montre du grand-père, planification de la semaine) est dans `regles.json`, sections `samedi` et `dimanche`.

Le résumé de chaque journée distingue les besoins passés sous le seuil d'alerte **éveillé** (à examiner) et **pendant le sommeil** (durée par besoin, attendu pour la soif la nuit).

## Vue fil de fer

La semaine se rejoue dans une vue isométrique fil de fer (`vue/index.html`, à ouvrir dans un navigateur) : appartement, escalier de l'immeuble et parcours de course, avec l'état de chaque pas (activité, pensée, besoins, émotions, objets, lumières et appareils).

```bash
# Recalculer les données de la vue après une génération de journées ou une modification du plan
python3 outils/exporter_vue.py
```

L'export lit la fiche, la géométrie du monde (`data/monde/croix-rousse.json`) et toutes les journées, puis calcule :
- le trajet de Thomas à chaque pas, porte par porte, et dans l'escalier (avec le détour par le local poubelles) ;
- sa position sur le parcours de course : descente des pentes, aller-retour le long de la Saône, remontée ;
- la position en 3D de chaque emplacement d'objet.

Il s'arrête si une liaison du plan n'a pas de porte ou si une pièce n'a pas de rectangle. Il affiche les distances entre pièces mesurées sur le plan, à comparer avec celles de la fiche.
