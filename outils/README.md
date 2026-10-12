# Outils

Génération des timelines des personnages, pas de 5 minutes par pas de 5 minutes.

Deux façons de produire une journée :
- **rédigée à la main** (`journees/<personnage>/<date>.py`), puis calculée par le moteur : c'est ainsi qu'ont été écrites les journées de référence (lundi à mercredi) de chaque personnage, qui servent à valider son agent ;
- **vécue par un agent autonome**, qui décide seul de chaque pas à partir de ses recettes et de ses règles : `agent.py` pour Thomas, `agent_epicier.py` pour Robert Chazal. La semaine officielle des deux personnages est vécue ainsi.

## Principe

| Ce qui est rédigé à la main (`journees/<personnage>/<date>.py`) | Ce qui est calculé (`moteur.py`) |
|---|---|
| Actions, pensées, rêves | Déplacements : chemin le plus court sur le plan, distance, durée, foulées ; escalier intérieur compté dès qu'un chemin l'emprunte |
| Événements vécus (catalogue de la fiche) | Lumière : interrupteurs selon les pièces sans fenêtre et le coucher du soleil ; une boutique éclairée pendant l'ouverture (`"eclairage": "permanent"`) ne se commande qu'à la main |
| Objets déplacés, appareils utilisés | Besoins à chaque pas (taux de la fiche) |
| Provisions consommées, achetées, prélevées au magasin | Émotions, uniquement à partir des événements, des besoins et du retour à l'état de base |
| Escaliers, parcours à pied et en voiture | Concentration selon l'activité, la fatigue et les émotions |
| Ventes, livraisons, reprises d'invendus (commerçant) | Stock du magasin produit par produit, recette encaissée en caisse (espèces), sur le compte (carte) ou sur l'ardoise (crédit) |

Chaque journée part de l'**état exact de la fin de la veille** (besoins, émotions, pièce, lumières, appareils, position de chaque objet). Le premier jour part de la fiche.

## Commandes

```bash
# Vérifier la fiche du personnage
python3 outils/verifier_fiche.py data/personnages/thomas-berthier.json

# Calculer une journée de référence rédigée à la main (la veille doit déjà être calculée)
python3 outils/generer_journee.py 2010-03-08
python3 outils/generer_journee.py 2010-03-09
python3 outils/generer_journee.py 2010-03-08 --personnage robert-chazal
```

Chaque journée de référence est écrite dans `data/references/<personnage>/<date>.json` (données complètes) et `<date>.md` (version lisible).

## Contrôles de cohérence

La génération s'arrête avec un message « Incohérence » si :
- une journée ne compte pas exactement 288 pas, ou si deux activités se chevauchent ou laissent un trou ;
- un objet est déplacé depuis un endroit où il ne se trouve pas (sa position est suivie d'un jour à l'autre) ;
- un événement ou un produit n'existe pas dans la fiche ;
- une provision est consommée alors qu'il n'en reste pas assez (le stock est suivi d'un jour à l'autre) ;
- un produit est vendu, repris ou prélevé alors que le magasin n'en a plus ; les espèces, la caisse ou le coffre passeraient sous zéro ;
- la durée d'endormissement prévue par la journée ne correspond pas à l'état émotionnel au moment d'éteindre (45 minutes si l'anxiété ou l'excitation dépasse son seuil, 15 sinon).

Les besoins passés sous leur seuil d'alerte sont listés dans le résumé de chaque journée.

## Ajouter une journée

1. Copier la journée précédente dans `outils/journees/<personnage>/<date>.py` et réécrire son contenu. Une journée de commerçant reçoit l'état du matin (`rediger(etat)`) pour tenir le stock du magasin au fil de la rédaction ; les éléments communs (trajets en Kangoo, comptoir) sont dans `outils/journees/robert-chazal/commun.py`.
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
# Semaine officielle : Thomas d'abord, puis l'épicier, qui lit les visites de Thomas dans sa journée
python3 outils/simuler_agent.py 2010-03-08 2010-03-14 --dossier data/timelines/thomas-berthier
python3 outils/simuler_agent.py 2010-03-08 2010-03-14 --personnage robert-chazal --dossier data/timelines/robert-chazal

# Validation : l'agent revit lundi à mercredi, puis on compare à la référence
python3 outils/simuler_agent.py 2010-03-08 2010-03-10 --dossier data/simulations/thomas-berthier --sans-courses
python3 outils/comparer_journees.py data/references/thomas-berthier/2010-03-09.json data/simulations/thomas-berthier/2010-03-09.json
python3 outils/simuler_agent.py 2010-03-08 2010-03-10 --personnage robert-chazal --dossier data/simulations/robert-chazal
python3 outils/comparer_journees.py data/references/robert-chazal/2010-03-09.json data/simulations/robert-chazal/2010-03-09.json
```

`simuler_agent.py` choisit l'agent d'après `data/agents/<personnage>/regles.json` : `"type": "commerce"` désigne l'agent de commerçant.

### Courses à l'épicerie

Le mardi, le jeudi et le samedi, Thomas descend à l'épicerie de Robert Chazal (`regles.json`, section `courses`) : en semaine après la fermeture de l'atelier, le samedi après le ménage. Il fait d'abord sa liste d'après son stock (fruits à compléter, produits sous leur seuil), vérifie que l'épicerie est ouverte (horaires de la fiche de Robert), descend la poubelle si elle est pleine, marche 500 m, achète au prix du catalogue de l'épicerie, paie en espèces ou par carte, rentre et range. Les achats augmentent son stock ; l'argent est suivi (espèces, compte).

### L'épicier

`agent_epicier.py` fait vivre Robert Chazal entre sa maison de Villeurbanne et sa boutique de la Croix-Rousse, à 5,2 km en Kangoo. Ses connaissances sont dans `data/agents/robert-chazal/` : `blocs.json` (scènes : lever, trajets, livraisons, déjeuner, soirées, lundi, dimanche ; reprises des journées de référence ou rédigées pour la fin de semaine), `regles.json` (horaires, seuils, habitudes du comptoir, courses de la maison) et `pensees.json`.

- **Clientèle** (`clientele.py`) : à chaque pas d'ouverture, un nombre de clients anonymes tiré autour de l'affluence de l'heure (loi de Poisson), chacun avec un panier d'un à quatre articles selon le moment de la journée ; les habitués de la fiche viennent à leur heure avec leur panier et leurs propos du jour. Le flux ne dépend que de la date et de l'heure ; ce qui est vendu dépend du stock (un produit épuisé est une rupture).
- **Comptoir** : café à 09:30 et 16:30, verres d'eau, toilettes pendant un creux, Le Progrès, bavardage avec le buraliste, les Grosses Têtes à la radio, étal à remplir ou à resserrer.
- **Magasin** : pain livré chaque matin (invendus repris), grossiste le mardi et le vendredi selon le bon de commande du lundi et du jeudi soir (chaque produit ramené à son stock cible), caisse vidée au coffre à midi et le soir, dépôt à la banque le lundi.
- **Maison** : le soir, il prélève au magasin ce qui manque pour les repas de Josiane (menus de la fiche, avec leurs ingrédients) et ses propres provisions ; après une nuit trop courte, il oublie le cabas.
- **Soirées** : télévision écourtée par la fatigue, match du mercredi, belote du samedi, cinéma du lundi ; le dimanche, vote et randonnée dans les monts d'Or.

Aux pas où la journée de Thomas le fait entrer dans la boutique, Robert le sert : mêmes répliques (`data/monde/echanges.json`), mêmes achats, même paiement. Le match du mercredi (`data/monde/evenements.json`) est vécu aux mêmes minutes par les deux personnages.

Les résultats des validations sont dans `data/simulations/thomas-berthier/VALIDATION.md` et `data/simulations/robert-chazal/VALIDATION.md`.

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

La semaine se rejoue dans une vue isométrique fil de fer (`vue/index.html`, à ouvrir dans un navigateur), à plusieurs échelles : le logement (l'appartement de Thomas, la boutique ou la maison de Robert), l'immeuble, la rue (de chez Thomas à l'épicerie), le parcours de course (pentes et quais de Saône), et pour Robert le trajet en Kangoo (Croix-Rousse, Rhône, Villeurbanne), le cinéma de la Cité internationale, l'école où il vote et les monts d'Or. On choisit le personnage suivi (Thomas ou Robert) ; l'autre reste visible. Le panneau donne l'état de chaque pas : activité, pensée, besoins, émotions, objets portés, argent, lumières et appareils.

```bash
# Recalculer les données de la vue après une génération de journées ou une modification du plan
python3 outils/exporter_vue.py
```

L'export lit la géométrie du monde (`data/monde/croix-rousse.json`), les fiches des personnages qui y ont un logement et toutes leurs journées. Tout est exprimé dans un seul repère, en mètres. Il calcule :
- le trajet de chaque personnage à chaque pas, porte par porte, par les escaliers (avec le détour par le local poubelles), puis dans les rues : courses à l'épicerie, descente des pentes, aller-retour le long de la Saône, remontée ; pour un personnage qui a plusieurs lieux (boutique et maison), les trajets en voiture et à pied décrits dans `trajets_personnages`, la position suivant la part du trajet faite ;
- l'altitude de chaque bâtiment et des rues d'après le relief (plateau, pentes vers la Saône et le Rhône, monts d'Or) ;
- la position en 3D de chaque emplacement d'objet ;
- les immeubles ordinaires le long des rues et les arbres, générés de façon déterministe.

Il s'arrête si une liaison du plan d'une fiche n'a pas de porte ou si une pièce n'a pas de rectangle. Il affiche les distances entre pièces mesurées sur le plan, à comparer avec celles des fiches.
