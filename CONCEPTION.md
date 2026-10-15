# Paradoxe — document de conception

## Le concept

Une **mini-ville de 2010** dont chaque habitant vit sa vie de façon déterministe, à quelques minutes près : routines, besoins, émotions, objets, déplacements. Cette vie constitue **l'histoire de référence**.

Le joueur incarne un **voyageur venu du futur**. Il arrive dans cette époque avec une mission et doit l'accomplir **sans provoquer de paradoxe**.

## L'histoire

**2035.** Un virus végétal a détruit toute végétation sur Terre : arbres, plantes, légumes. La plupart de la population est morte de faim. Le voyage dans le temps est devenu une réalité, et **John** est envoyé dans le passé pour changer l'avenir.

**L'origine du virus.** Il dormait dans une **branche fossilisée**, profondément enfouie sous l'**arrière-boutique de l'épicerie Chazal**, Grande-Rue de la Croix-Rousse : sous la dalle de béton et deux mètres de terre. En **2012**, la boutique est démolie pour construire un immeuble ; les terrassements mettent la branche à l'air libre, et le virus se propage.

**La mission de John.** Arrivé en **mars 2010**, deux ans avant la démolition, il doit trouver la branche et la **détruire en la brûlant sur place**, sans que l'histoire de référence ne dérape : si les habitants remarquent ce qui s'est passé dans l'arrière-boutique et que la divergence s'emballe, le paradoxe survient.

**Ce qui rend la mission difficile.** Robert Chazal est à la boutique du mardi au samedi de 06:30 à 19:15, et le dimanche matin ; le lundi, jour de fermeture, il y passe tout de même vers 09:10 prendre la recette au coffre de l'arrière-boutique, et revient vérifier la porte de derrière à 09:30 ; découper une dalle fait un bruit qu'on entend dans toute la boutique ; creuser deux mètres prend des heures ; la terre, la poussière, l'odeur de brûlé et le béton neuf laissent des traces que Robert peut remarquer en revenant, et raconter. Le joueur doit choisir son moment (la nuit, le lundi après le passage de Robert), ses gestes (crocheter plutôt que forcer), et effacer ce qu'il laisse (nettoyer, aérer, recouvrir).

Le terrain de jeu, c'est la connaissance fine de la vie des habitants : savoir qui sort à quelle heure, qui remarque quoi, quel objet compte pour qui.

## Le voyageur

- Il cherche à être **compatible avec l'époque** : vêtements, argent, comportement, objets de 2010.
- Il peut être vu : pour un habitant, il n'est qu'un **passant**, sans conséquence.
- Un anachronisme visible (objet ou comportement qui n'existe pas en 2010) est en revanche une anomalie qu'un habitant peut remarquer.
- Sa mission : la branche fossilisée de l'arrière-boutique (voir « L'histoire »).

## Le paradoxe

### Ce qui n'est pas un paradoxe
- Être vu par un habitant.
- Une interaction minime : entrer dans un bar, boire un café, croiser quelqu'un dans la rue.

Ces écarts sont **absorbés** : le temps est **résilient**. C'est une règle du jeu ; en physique, l'idée d'un temps qui « se referme » reste une hypothèse (principe d'auto-cohérence de Novikov), pas un résultat démontré.

### Ce qui crée un paradoxe
Une intervention du voyageur sur une **action** d'un habitant, qui modifie **en cascade** un nombre croissant de choses : décisions, rencontres, objets, horaires, puis la vie d'autres habitants.

### Mesure envisagée
Deux mondes sont simulés en parallèle :
- le **monde de référence**, sans le voyageur ;
- le **monde joué**, avec ses interventions.

Le jeu compare les deux à chaque pas, en distinguant deux niveaux :

| Niveau | Exemples | Traitement |
|---|---|---|
| **Détails** | Émotions légèrement différentes, quelques secondes d'écart, une tasse de café en moins dans le stock d'un bar | Tolérés et absorbés avec le temps |
| **Faits** | Une action faite ou non, une décision, un objet qui change de main, une rencontre, un retard qui en entraîne d'autres | Comptés dans la divergence |

La **divergence** suit le nombre de faits différents et le nombre d'habitants touchés au fil du temps :
- si elle reste faible et se résorbe, le temps l'a absorbée ;
- si elle **s'amplifie** (effet de cascade), le paradoxe approche ; au-delà d'un seuil, il survient.

Certains **événements-clés** (importants pour le futur) pourront compter plus que les autres.

## Conséquences techniques

1. **Habitants autonomes** : chaque habitant décide lui-même de ses actions (routines, besoins, perceptions). Sans voyageur, la simulation doit reproduire exactement l'histoire de référence.
2. **Perception** : ce que chaque habitant voit, entend et remarque. Ce qu'il croit est séparé de ce qui est réel.
3. **Chaînes de causes** : chaque fait garde la trace de ce qui l'a provoqué, pour suivre une cascade jusqu'à son origine.
4. **Temps variable** : un pas de 5 minutes par défaut, un pas plus fin quand le voyageur est proche d'un habitant.
5. **Niveau de détail variable** : simulation complète pour les habitants proches du voyageur ou touchés par une cascade, simulation simplifiée pour les autres, afin de faire vivre une ville entière.

## Feuille de route

| Étape | Contenu | État |
|---|---|---|
| 1 | Un habitant (Thomas Berthier), semaine de référence rédigée et vérifiée par le moteur | Fait : lundi à mercredi rédigés (`data/references/`) |
| 2 | Thomas autonome : le moteur décide de ses actions et reproduit la semaine de référence | Fait : référence reproduite (voir `data/simulations/thomas-berthier/VALIDATION.md`) ; la semaine entière est vécue par l'agent, courses comprises, avec ses distractions de fin de semaine (forum d'horlogerie, cinéma, vote, promenade) |
| 3 | Perception : ce que Thomas voit, entend, remarque | Fait : ce qu'il croit est séparé de ce qui est réel (`outils/perception.py`) ; il voit, entend, remarque les écarts et décide d'après ses croyances (il cherche un objet qui n'est pas à sa place). Sans perturbation, la semaine est inchangée. Scénario de test : les clés déplacées pendant la nuit (`data/scenarios/`) |
| 4 | Le voyageur dans le monde de Thomas ; mesure de la divergence entre les deux mondes | Commencé : le voyageur agit dans le quartier (`outils/voyageur.py` : déplacer un objet, retenir un habitant, acheter, parler) ; le monde joué est comparé au monde de référence (`outils/divergence.py`), faits comptés et détails tolérés, habitants touchés directement ou par cascade, verdict (absorbée, persistante, cascade, paradoxe). Sept scénarios dans `data/voyageur/` : demander l'heure à Thomas est absorbé dans l'heure ; le retenir à l'heure de ses courses touche Robert puis se résorbe le jeudi ; retenir Robert à l'heure de la belote touche quatre habitants : paradoxe. Chaîne des causes : chaque fait différent est rattaché à ce qui l'a provoqué (intervention, absence de l'autre, rencontre manquée, besoins décalés…), et l'arbre remonte une cascade jusqu'au voyageur (reconstruit en comparant les deux mondes). Anachronismes : ce que porte ou utilise le voyageur (`data/monde/epoque.json`) peut être remarqué par les habitants présents, selon la visibilité, leur attention et leur concentration ; l'anomalie se raconte de bouche à oreille, et la chaîne des causes suit la rumeur (un paiement par téléphone vu par Robert atteint les cinq habitants en un jour et demi : paradoxe ; le même achat avec un équipement d'époque ne change aucun fait) |
| 5 | Plusieurs habitants et lieux partagés (rue, bar, commerces) | Commencé : Robert Chazal, l'épicier, a une fiche aussi complète que celle de Thomas, trois journées de référence rédigées et un agent qui les reproduit (voir `data/simulations/robert-chazal/VALIDATION.md`) ; magasin tenu produit par produit, clientèle déterministe, maison à Villeurbanne, loisirs ; scène partagée au comptoir, dont le conseil de film du samedi qui décide la soirée de Thomas ; match du mercredi vécu par les deux |
| 6 | La mini-ville : génération des habitants, niveaux de détail | Commencé : habitant générique (`outils/habitant.py`), un seul moteur pour tous, sans code propre à un personnage : routines de la fiche (chaque étape nomme une action), catalogue d'actions commun (`data/monde/actions.json`), choix par l'utilité. Sur les jours de semaine de Thomas : 84 à 91 % des pas dans la même pièce que l'agent écrit à la main. Objets et provisions : les actions nomment les objets par leur rôle (lunettes gardées pendant le travail, clés prises en sortant, tasse et cafetière), la fiche dit lequel tient chaque rôle ; les repas consomment les menus de la fiche (ingrédients, plat préparé pour plusieurs repas, portion), les pauses ses collations ; lundi, chaque objet est à la même place que dans la journée de référence 97 % du temps, chaque provision au même stock 98 %. Approvisionnement : Thomas va faire ses courses à l'épicerie de Robert (liste d'après ses cibles, ses seuils et ses menus jusqu'aux prochaines courses, paiement), Robert prélève dans sa boutique pour la maison en fermant. La boutique de Robert vit avec le même moteur : livraisons du boulanger et du grossiste, clients du flux déterministe, caisse, coffre, dépôt à la banque. Thomas vit dans le quartier avec Robert, Josiane et les Morel : à l'épicerie, il retrouve Robert, qui lui vend ses courses sur le stock de sa boutique ; seul le stock d'un commerce est un état commun (les logements, pas encore). Restent les périmés du dimanche. Robert vit aussi avec ce moteur (mardi : même pièce que sa journée de référence 90 % des pas). Josiane, sa femme, est le premier habitant créé directement pour lui ; le quartier (`outils/quartier.py`) fait vivre ensemble n'importe quels habitants : une fiche ne décrit que ce qui est propre à la personne, le monde (`data/monde/` : humain, calendrier, lieux, logements partagés, actions, interactions par type de relation) fournit le reste. Rencontres, absences, conversations à partir de modèles, ce que chacun apprend des autres. Logements partagés : lumières, appareils, provisions et objets d'un même toit sont communs à ses occupants (`outils/logements.py`) ; les repas du foyer sont cuisinés une fois pour tous (Josiane cuisine, le garde-manger baisse pour deux). Exemple : Robert, Josiane et leurs voisins Gérard et Monique Morel |
| 7 | Missions du voyageur | Commencé : la mission principale, la branche fossilisée (`data/missions/branche-fossile.json`) ; les gestes de John (`data/monde/gestes.json`) font avancer la mission, s'entendent, se voient et laissent des traces que les habitants peuvent remarquer et raconter. En plein jour, Robert entend la scie : paradoxe ; le lundi sans rien effacer, Robert trouve les traces le mardi : paradoxe ; le lundi avec soin (crocheter, nettoyer, aérer, recouvrir) : réussie, aucun fait changé. Réactions : chez lui, un habitant va voir d'où vient un bruit, surprend John (qui s'enfuit pour la journée), appelle la police, fait changer la serrure ; sa journée en est changée, il devient plus vigilant, et la serrure neuve ne se crochète plus (surpris le samedi, John ne peut pas revenir le dimanche par la même porte). Restent la démolition de 2012 et d'autres missions |
| 8 | Interface de jeu | Commencée : vue isométrique fil de fer (`vue/`) : logements, immeubles, rues, parcours, trajets en voiture jusqu'à Villeurbanne et aux monts d'Or, sorties à pied de Thomas (cinéma, mairie du 4e, Gros Caillou), deux personnages ; plan à valider. Interface de jeu (`vue/jouer.html` et `outils/serveur_jeu.py`) : le joueur compose le plan de John, lance la semaine et voit aussitôt le résultat de la mission et la cascade. Page du quartier (`vue/quartier.html`) : la semaine de chaque habitant, où il est et avec qui, et les alertes du contrôle de cohérence (`outils/controler_quartier.py`). Page du voyageur (`vue/divergence.html`) : pour chaque scénario, la frise des faits différents habitant par habitant, les deux mondes à l'instant choisi, la chaîne des causes |
