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

- Deux personnages simulés : Thomas Berthier et Robert Chazal, l'épicier chez qui il fait ses courses. Thomas vit seul ; Robert vit avec sa femme Josiane, qui n'est pas simulée (ses paroles et ses gestes n'apparaissent que tels que Robert les vit).
- Les passants, les autres clients, les livreurs, les spectateurs du cinéma et les assesseurs des bureaux de vote ne sont pas simulés.
- Aucun contact à distance (téléphone, SMS, e-mail, réseau social).
- Thomas reste chez lui, sauf pour courir seul, faire ses courses (mardi, jeudi, samedi) et, en fin de semaine, ses sorties à pied : le cinéma le samedi soir, sur le conseil de Robert, et le vote du dimanche suivi d'une promenade jusqu'au Gros Caillou. Robert va et vient en Kangoo entre sa maison de Villeurbanne et sa boutique ; ses autres sorties : le coffre de la banque le lundi matin, le cinéma avec Josiane le lundi soir, le vote et une randonnée dans les monts d'Or le dimanche.
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
| `commerce` | Pour un commerçant : horaires, livraisons, affluence par heure, paniers des clients, rayons de la boutique dans l'ordre du tour d'un client, catalogue (rayon, prix, stock initial, stock cible), habitués et leurs propos du jour |
| `lieux`, `trajets` | Domicile, épicerie, cinéma, bureau de vote et parcours (course, épicerie, sorties à pied) détaillés par segments (distance, dénivelé, durée) |
| `immeuble` | Étage, escalier (66 marches), durées et efforts de montée et de descente |
| `domicile` | Pièces (avec ou sans fenêtre), plan des liaisons et distances, petits déplacements par activité, mobilier, équipements, provisions chiffrées et plats préparés |
| `menus_prevus` | Repas planifiés pour chaque jour ; chez Robert, avec leurs ingrédients (pour le couple) |
| `voiture`, `vie_interieure.loisirs` | Chez Robert : la Kangoo ; cinéma, randonnée, belote, potager, journal, radio. Chez Thomas : course, montre du grand-père, lecture, musique, radio, forums d'horlogerie (en lecture), cinéma, promenade |
| `objets` | Objets avec leur emplacement réel au départ |
| `connaissances` | Ce que le personnage sait ; ses croyances sur l'emplacement des objets |
| `habitudes` | Automatismes (gestes systématiques) et routines horaires de chaque jour |
| `agenda_semaine` | Activités datées de la semaine |
| `objectifs` | Buts de la semaine, échéances, priorités |

## Timelines

Les journées vécues sont stockées dans `data/timelines/<personnage>/<date>.json`, avec une version lisible `<date>.md`.

Chaque pas de 5 minutes contient : heure, pièce, posture, routine suivie, activité, action, pensée (voix intérieure), rêve et phase de sommeil la nuit, déplacement (chemin, distance, durée, foulées, escalier, parcours à pied ou en voiture), interrupteurs actionnés, appareils allumés, objets déplacés, provisions consommées, achetées ou préparées avec le stock restant, mouvements d'argent (espèces, compte, caisse, coffre, ardoises), événements vécus avec leur effet sur chaque émotion, besoins et émotions à la fin du pas. Chez un commerçant : clients servis, ventes (produit, quantité, prix, paiement), livraisons, reprises d'invendus, prélèvements pour la maison, ruptures, et le stock du magasin restant.

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
| `timelines/robert-chazal/2010-03-08.json` | Lundi 8 mars : banque, grand ménage, comptes, bon de commande, potager, cinéma avec Josiane |
| `timelines/robert-chazal/2010-03-09.json` | Mardi 9 mars : livraisons, Mme Ferrand et M. Benali, l'horloger, omelette, coucher avancé |
| `timelines/robert-chazal/2010-03-10.json` | Mercredi 10 mars : ardoise des étudiantes, croque-monsieur, Real Madrid – Lyon |
| `timelines/robert-chazal/2010-03-11.json` | Jeudi 11 mars : cabas oublié, l'horloger, bon de commande pour vendredi |
| `timelines/robert-chazal/2010-03-12.json` | Vendredi 12 mars : grossiste, ardoise réglée |
| `timelines/robert-chazal/2010-03-13.json` | Samedi 13 mars : l'horloger à 11:50, belote avec les Morel |
| `timelines/robert-chazal/2010-03-14.json` | Dimanche 14 mars : boutique le matin, rôti, vote, randonnée dans les monts d'Or |
| `references/<personnage>/2010-03-08.json` … `2010-03-10.json` | Lundi à mercredi rédigés à la main : la référence qui valide chaque agent (Thomas sans les courses) |

Toutes les journées de `timelines/` sont vécues par les agents autonomes (`outils/simuler_agent.py`). Les journées rédigées à la main sont gardées dans `references/` et calculées par `outils/generer_journee.py`. Voir `outils/README.md`.

## Monde

| Fichier | Contenu |
|---|---|
| `monde/croix-rousse.json` | Géométrie partagée, dans un seul repère : relief (plateau, pentes vers la Saône et le Rhône, monts d'Or), rues de la Croix-Rousse et de Villeurbanne, place, immeubles de Thomas et de l'épicerie, maison de Robert (étages, escaliers), logements (pièces, portes, fenêtres, mobilier, emplacements des objets, postes), Saône, Rhône, trajets de course, d'épicerie, en Kangoo et à pied. **Proposition à valider.** |
| `monde/croix-rousse.json` (boutique) | Places précises de la boutique (rayons et caisse pour un client, places de travail de Robert) et allées (`circulation`) que suit un client entre deux rayons |
| `monde/echanges.json` | Répliques partagées par deux personnages qui se rencontrent (Thomas et Robert au comptoir, dont le conseil de film du samedi qui décide la soirée de Thomas) |
| `monde/evenements.json` | Événements réels vécus aux mêmes minutes par plusieurs habitants (match Real Madrid – Lyon) |

Repère : x vers l'est le long de la rue d'Austerlitz, y vers le nord, z vers le haut (0 au niveau des rues du plateau), en mètres.

## Agents et simulations

| Dossier | Contenu |
|---|---|
| `agents/<personnage>/` | Connaissances de l'agent autonome : plan, recettes, travaux, séances, repas, modèles de pensées |
| `simulations/<personnage>/` | Lundi à mercredi revécus par l'agent, pour les comparer à la référence, et rapport `VALIDATION.md` |

## Personnages

| Fichier | Personnage |
|---|---|
| `personnages/thomas-berthier.json` | Thomas Berthier, 31 ans, horloger indépendant à Lyon (cas d'étude n°1) |
| `personnages/robert-chazal.json` | Robert Chazal, 58 ans, épicier de la Grande-Rue de la Croix-Rousse, marié à Josiane, vit à Villeurbanne (personnage n°2) |
