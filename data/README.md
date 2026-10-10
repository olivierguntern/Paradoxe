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
| `etat_initial` | Lieu, activité, besoins et émotions au premier pas de la semaine |
| `besoins` | Évolution de chaque besoin par pas de 5 minutes et ce qui le satisfait |
| `competences`, `biographie` | Savoir-faire et passé daté |
| `personnes_en_memoire` | Personnes qui existent seulement dans ses souvenirs et ses pensées |
| `economie`, `travail` | Argent, charges, horaires, travaux en cours et ordre de priorité |
| `lieux`, `trajets` | Domicile et parcours de course |
| `domicile` | Pièces, mobilier, équipements, provisions |
| `menus_prevus` | Repas planifiés pour chaque jour |
| `objets` | Objets avec leur emplacement réel au départ |
| `connaissances` | Ce que le personnage sait ; ses croyances sur l'emplacement des objets |
| `habitudes` | Automatismes (gestes systématiques) et routines horaires de chaque jour |
| `agenda_semaine` | Activités datées de la semaine |
| `objectifs` | Buts de la semaine, échéances, priorités |

## Timelines

Les journées vécues sont stockées dans `data/timelines/<personnage>/<date>.json`, avec une version lisible `<date>.md`.

Chaque pas de 5 minutes contient : heure, pièce, routine suivie, activité, action, pensée (voix intérieure), rêve et phase de sommeil la nuit, objets déplacés, provisions consommées, besoins et émotions à la fin du pas.

| Fichier | Contenu |
|---|---|
| `timelines/thomas-berthier/2010-03-08.json` | Lundi 8 mars 2010, journée de référence rédigée à la main |

## Personnages

| Fichier | Personnage |
|---|---|
| `personnages/thomas-berthier.json` | Thomas Berthier, 31 ans, horloger indépendant à Lyon (cas d'étude n°1) |
