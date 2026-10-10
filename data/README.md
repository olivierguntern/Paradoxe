# Dataset des personnages

Chaque personnage est décrit dans un fichier JSON de `data/personnages/`. Cette fiche est le point de départ de la simulation de sa timeline.

## Conventions

| Élément | Convention |
|---|---|
| Période étudiée | du lundi 8 mars 2010 00:00 au dimanche 14 mars 2010 23:55 |
| Pas de temps | 5 minutes (2016 pas sur la semaine) |
| Heures | `HH:MM` ou `AAAA-MM-JJTHH:MM`, toujours multiples de 5 minutes |
| Besoins | 0 à 100 (100 = pleinement satisfait, 0 = critique) |
| Émotions, traits, relations | 0 à 1 |
| Identifiants | en minuscules avec tirets (`thomas-berthier`, `obj-cles`) ; ils relient les sections entre elles |
| Simulation | déterministe : mêmes conditions de départ, même timeline |

## Sections d'une fiche

| Section | Contenu |
|---|---|
| `meta` | Période, pas de temps, échelles, faits réels utilisés |
| `identite`, `apparence`, `sante` | Qui est le personnage, son corps, son sommeil, ses consommations |
| `personnalite` | Big Five, traits, qualités, défauts, ponctualité |
| `vie_interieure` | Valeurs, croyances, peurs, désirs, secrets, pensées récurrentes, préoccupations, déclencheurs émotionnels, mécanismes d'adaptation |
| `etat_initial` | Lieu, activité, besoins et émotions au premier pas de la semaine |
| `besoins` | Évolution de chaque besoin par pas de 5 minutes et ce qui le satisfait |
| `competences`, `biographie` | Savoir-faire et passé daté |
| `relations` | Personnes connues, intimité, confiance, état actuel de la relation |
| `economie`, `travail` | Argent, charges, horaires et travaux en cours |
| `lieux`, `trajets` | Lieux fréquentés et temps de déplacement |
| `domicile` | Pièces, mobilier, provisions |
| `objets` | Objets avec leur emplacement réel au départ |
| `connaissances` | Où le personnage *croit* que sont les objets, ce qu'il sait et ce qu'il ignore |
| `habitudes` | Automatismes (gestes systématiques) et routines horaires |
| `agenda_semaine` | Rendez-vous datés et objets nécessaires |
| `objectifs` | Buts de la semaine, échéances, priorités |

## Réalité et croyance

Les objets ont deux positions :
- `objets[].emplacement_initial` : où l'objet se trouve **réellement** ;
- `connaissances.emplacements_crus` : où le personnage **pense** qu'il se trouve.

Un écart entre les deux produit une conséquence dans sa timeline (recherche, retard, oubli). C'est l'un des points d'entrée des paradoxes.

## Personnages

| Fichier | Personnage |
|---|---|
| `personnages/thomas-berthier.json` | Thomas Berthier, 31 ans, horloger à Lyon (cas d'étude n°1) |
