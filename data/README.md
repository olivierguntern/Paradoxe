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

## Contraintes du test

- Deux personnages simulés : Thomas Berthier et Robert Chazal, l'épicier chez qui il fait ses courses. Chacun vit seul.
- Les passants, les autres clients et les livreurs ne sont pas simulés.
- Aucun contact à distance (téléphone, SMS, e-mail, réseau social).
- Thomas reste chez lui, sauf pour courir seul et faire ses courses (mardi, jeudi, samedi) ; Robert ne quitte pas son immeuble.
- Aucun paradoxe ni élément perturbateur : les croyances correspondent toujours à la réalité. Les paradoxes seront introduits plus tard, de l'extérieur.

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

Chaque pas de 5 minutes contient : heure, pièce, posture, routine suivie, activité, action, pensée (voix intérieure), rêve et phase de sommeil la nuit, déplacement (chemin, distance, durée, foulées, escalier, parcours extérieur), interrupteurs actionnés, appareils allumés, objets déplacés, provisions consommées, achetées ou préparées avec le stock restant, mouvements d'argent (espèces, compte, caisse), événements vécus avec leur effet sur chaque émotion, besoins et émotions à la fin du pas.

Le stock de provisions est suivi d'un jour à l'autre : une journée qui consomme ce qui n'existe plus est refusée.

Les émotions ne sont jamais fixées à la main : elles sont calculées à partir des événements, des besoins et du retour à l'état de base, selon `modele_emotionnel`.

| Fichier | Contenu |
|---|---|
| `timelines/thomas-berthier/2010-03-08.json` | Lundi 8 mars : atelier, cuisine, première séance sur l'axe |
| `timelines/thomas-berthier/2010-03-09.json` | Mardi 9 mars : course à pied, Omega, courses à l'épicerie |
| `timelines/thomas-berthier/2010-03-10.json` | Mercredi 10 mars : fin de la Rolex, lessive, trempe de l'axe, Real Madrid – Lyon |
| `timelines/thomas-berthier/2010-03-11.json` | Jeudi 11 mars : course, validations, Zenith, courses à l'épicerie |
| `timelines/thomas-berthier/2010-03-12.json` | Vendredi 12 mars : Zenith en observation, gestion, dépose de l'ancien axe, fin de « La Route » |
| `timelines/thomas-berthier/2010-03-13.json` | Samedi 13 mars : ménage, courses, début de « Courir », montage de l'axe : la montre du grand-père bat de nouveau |
| `timelines/thomas-berthier/2010-03-14.json` | Dimanche 14 mars : sortie longue de 12 km, fin de « Courir », réglage après 24 h |
| `timelines/robert-chazal/2010-03-08.json` … `2010-03-14.json` | La semaine de l'épicier : fermeture du lundi, livraisons, service, visites de Thomas, match du mercredi, dimanche matin |
| `references/thomas-berthier/2010-03-08.json` … `2010-03-10.json` | Lundi à mercredi rédigés à la main, sans courses : la référence qui valide l'agent |

Toutes les journées de `timelines/` sont vécues par les agents autonomes (`outils/simuler_agent.py`). Les journées rédigées à la main sont gardées dans `references/` et calculées par `outils/generer_journee.py`. Voir `outils/README.md`.

## Monde

| Fichier | Contenu |
|---|---|
| `monde/croix-rousse.json` | Géométrie partagée, dans un seul repère : relief, rues, place, immeubles de Thomas et de l'épicerie (étages, escaliers), logements des deux personnages (pièces, portes, fenêtres, mobilier, emplacements des objets, postes), Saône, quais, trajets de course et d'épicerie. **Proposition à valider.** |
| `monde/echanges.json` | Répliques partagées par deux personnages qui se rencontrent (Thomas et Robert au comptoir) |
| `monde/evenements.json` | Événements réels vécus aux mêmes minutes par plusieurs habitants (match Real Madrid – Lyon) |

Repère : x vers l'est le long de la rue d'Austerlitz, y vers le nord, z vers le haut (0 au niveau des rues du plateau), en mètres.

## Agents et simulations

| Dossier | Contenu |
|---|---|
| `agents/<personnage>/` | Connaissances de l'agent autonome : plan, recettes, travaux, séances, repas, modèles de pensées |
| `simulations/<personnage>/` | Lundi à mercredi revécus par l'agent sans les courses, pour les comparer à la référence, et rapport `VALIDATION.md` |

## Personnages

| Fichier | Personnage |
|---|---|
| `personnages/thomas-berthier.json` | Thomas Berthier, 31 ans, horloger indépendant à Lyon (cas d'étude n°1) |
| `personnages/robert-chazal.json` | Robert Chazal, 58 ans, épicier de la Grande-Rue de la Croix-Rousse, veuf (personnage n°2) |
