# Dataset des personnages

Chaque personnage est décrit dans un fichier JSON de `data/personnages/`. Cette fiche est le point de départ de la simulation de sa timeline.

## Conventions

| Élément | Convention |
|---|---|
| Période étudiée | du lundi 8 mars 2010 00:00 au dimanche 14 mars 2010 23:55 |
| Pas de temps | 5 minutes (2016 pas sur la semaine) |
| Heures | `HH:MM` ou `AAAA-MM-JJTHH:MM`, toujours multiples de 5 minutes |
| Besoins | 0 à 100 (100 = pleinement satisfait, 0 = critique) |
| Émotions, traits, souvenirs | 0 à 1 |
| Identifiants | en minuscules avec tirets (`thomas-berthier`, `obj-cles`) ; ils relient les sections entre elles |
| Simulation | déterministe : mêmes conditions de départ, même timeline |

## Contraintes du premier test

- Le personnage vit seul : aucun autre personnage n'apparaît.
- Aucun contact à distance (téléphone, SMS, e-mail, réseau social).
- Il reste chez lui, sauf pour courir seul.
- Aucun paradoxe ni élément perturbateur : ses croyances correspondent toujours à la réalité. Les paradoxes seront introduits plus tard, de l'extérieur.

## Sections d'une fiche

| Section | Contenu |
|---|---|
| `meta` | Période, pas de temps, contraintes du test, échelles, faits réels utilisés |
| `identite`, `apparence`, `sante` | Qui est le personnage, son corps, son sommeil, ses consommations, son activité physique |
| `personnalite` | Big Five, traits, qualités, défauts |
| `vie_interieure` | Valeurs, croyances, peurs, désirs, pensées récurrentes, préoccupations, déclencheurs émotionnels, mécanismes d'adaptation |
| `modele_emotionnel` | Règles qui font découler les émotions des événements : état de base, demi-vies, catalogue d'événements, influence des besoins, concentration |
| `etat_initial` | Lieu, activité, besoins et émotions au premier pas de la semaine |
| `besoins` | Évolution de chaque besoin par pas de 5 minutes et ce qui le satisfait |
| `competences`, `biographie` | Savoir-faire et passé daté |
| `personnes_en_memoire` | Personnes qui existent seulement dans ses souvenirs et ses pensées |
| `economie`, `travail` | Argent, charges, horaires, travaux en cours et ordre de priorité |
| `lieux`, `trajets` | Domicile et parcours de course détaillés par segments (distance, dénivelé, durée) |
| `immeuble` | Étage, escalier (66 marches), durées et efforts de montée et de descente |
| `domicile` | Pièces (avec ou sans fenêtre), plan des liaisons et distances, petits déplacements par activité, mobilier, équipements, provisions chiffrées et plats préparés |
| `menus_prevus` | Repas planifiés pour chaque jour |
| `objets` | Objets avec leur emplacement réel au départ |
| `connaissances` | Ce que le personnage sait ; ses croyances sur l'emplacement des objets |
| `habitudes` | Automatismes (gestes systématiques) et routines horaires de chaque jour |
| `agenda_semaine` | Activités datées de la semaine |
| `objectifs` | Buts de la semaine, échéances, priorités |

## Timelines

Les journées vécues sont stockées dans `data/timelines/<personnage>/<date>.json`, avec une version lisible `<date>.md`.

Chaque pas de 5 minutes contient : heure, pièce, posture, routine suivie, activité, action, pensée (voix intérieure), rêve et phase de sommeil la nuit, déplacement (chemin, distance, durée, foulées, escalier, parcours extérieur), interrupteurs actionnés, appareils allumés, objets déplacés, provisions consommées ou plats préparés avec le stock restant, événements vécus avec leur effet sur chaque émotion, besoins et émotions à la fin du pas.

Le stock de provisions est suivi d'un jour à l'autre : une journée qui consomme ce qui n'existe plus est refusée.

Les émotions ne sont jamais fixées à la main : elles sont calculées à partir des événements, des besoins et du retour à l'état de base, selon `modele_emotionnel`.

| Fichier | Contenu |
|---|---|
| `timelines/thomas-berthier/2010-03-08.json` | Lundi 8 mars 2010 : atelier, cuisine, première séance sur l'axe |
| `timelines/thomas-berthier/2010-03-09.json` | Mardi 9 mars 2010 : course à pied (escaliers, quais de Saône), Rolex, les pivots |
| `timelines/thomas-berthier/2010-03-10.json` | Mercredi 10 mars 2010 : fin de la Rolex, pendule, lessive, trempe de l'axe, Real Madrid – Lyon |
| `timelines/thomas-berthier/2010-03-11.json` | Jeudi 11 mars 2010 : **généré par l'agent autonome** (course, validations, Zenith, polissage des pivots) |
| `timelines/thomas-berthier/2010-03-12.json` | Vendredi 12 mars 2010 : **généré par l'agent autonome** (Zenith en observation, gestion, dépose de l'ancien axe, fin du livre) |
| `timelines/thomas-berthier/2010-03-13.json` | Samedi 13 mars 2010 : **généré par l'agent autonome** (ménage, sieste, montage de l'axe : la montre du grand-père bat de nouveau) |
| `timelines/thomas-berthier/2010-03-14.json` | Dimanche 14 mars 2010 : **généré par l'agent autonome** (sortie longue de 12 km, réglage après 24 h, planification de la semaine) |

Lundi à mercredi sont rédigés à la main et calculés par `outils/generer_journee.py` ; de jeudi à dimanche, les journées sont vécues par l'agent autonome (`outils/simuler_agent.py`). La semaine complète (2016 pas) est donc disponible. Voir `outils/README.md`.

## Agents et simulations

| Dossier | Contenu |
|---|---|
| `agents/<personnage>/` | Connaissances de l'agent autonome : plan, recettes, travaux, séances, repas, modèles de pensées |
| `simulations/<personnage>/` | Journées vécues par l'agent à partir de la fiche, pour les comparer à la référence, et rapport `VALIDATION.md` |

## Personnages

| Fichier | Personnage |
|---|---|
| `personnages/thomas-berthier.json` | Thomas Berthier, 31 ans, horloger indépendant à Lyon (cas d'étude n°1) |
