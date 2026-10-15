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

Le mardi, le jeudi et le samedi, Thomas descend à l'épicerie de Robert Chazal (`regles.json`, section `courses`) : en semaine après la fermeture de l'atelier, le samedi après le ménage. Il fait d'abord sa liste d'après son stock (fruits à compléter, produits sous leur seuil), y ajoute ce que demanderaient ses déjeuners et dîners d'ici aux prochaines courses et les envies notées dans ses menus (`pour_les_repas` : un pain de campagne le samedi, pour le brunch du dimanche), vérifie que l'épicerie est ouverte (horaires de la fiche de Robert), descend la poubelle si elle est pleine, marche 500 m, achète au prix du catalogue de l'épicerie, paie en espèces ou par carte, rentre et range. Les achats augmentent son stock ; l'argent est suivi (espèces, compte).

Dans la boutique, la visite tient en deux pas. D'abord, il prend un panier près de la porte et fait le tour des rayons où se trouvent ses articles, dans l'ordre de la boutique (étal des fruits et légumes, rayons d'épicerie, rayon central, vitrine réfrigérée : champ `rayon` du catalogue de l'épicier). Ensuite, il va à la caisse, demande le pain (rangé derrière le comptoir), et Robert tape les articles et l'encaisse. Pendant le tour des rayons, Robert continue son travail : à la caisse s'il sert d'autres clients, sinon à l'endroit de sa tâche (bout de l'étal, rayons, vitrine réfrigérée ; `postes_boutique` dans `regles.json`). Chaque pas peut indiquer l'endroit précis de la pièce (`poste`) ou une liste d'arrêts ; la vue suit les allées de la boutique (`circulation` dans le monde) et marque un temps devant chaque rayon.

### Distractions et sorties de Thomas

Du lundi au jeudi, la journée de Thomas reste celle qui a été validée sur les journées de référence. En fin de semaine (`regles.json`, sections `distractions` et `sorties`) :

- **Vendredi soir** : la semaine de travail finie, il lit un forum d'horlogerie sur le netbook avant le temps libre (lecture seule, sans y écrire : la fiche exclut tout contact à distance).
- **Samedi** : à l'épicerie, Robert lui conseille « The Ghost Writer » (réplique `conseil` de `data/monde/echanges.json`, lue par les deux agents). L'agent de Thomas en tire sa décision : il vérifie l'horaire sur le netbook, avance son dîner, va à pied à l'UGC Ciné Cité Internationale (2,4 km par le boulevard, la montée de la Boucle et le pont Winston-Churchill), paie sa place, voit le film et rentre à pied ; il va voir la montre du grand-père avant de se coucher. Sans conseil, la soirée du samedi reste la soirée habituelle.
- **Dimanche** : brunch avec le pain de campagne acheté la veille ; après la planification de la semaine, il va voter au premier tour des régionales à la mairie du 4e, marche jusqu'au Gros Caillou et rentre ; le soir, la radio donne les résultats.

Avant de partir, il passe aux toilettes ou boit un verre d'eau si le besoin passerait sous son seuil d'alerte avant son retour (même règle qu'avant une séance sur la montre).

### L'épicier

`agent_epicier.py` fait vivre Robert Chazal entre sa maison de Villeurbanne et sa boutique de la Croix-Rousse, à 5,2 km en Kangoo. Ses connaissances sont dans `data/agents/robert-chazal/` : `blocs.json` (scènes : lever, trajets, livraisons, déjeuner, soirées, lundi, dimanche ; reprises des journées de référence ou rédigées pour la fin de semaine), `regles.json` (horaires, seuils, habitudes du comptoir, courses de la maison) et `pensees.json`. `outils/construire_scenes_robert.py` reconstruit `blocs.json` : il rejoue les journées de référence pour en extraire les scènes et y ajoute celles qui sont rédigées pour la fin de semaine.

- **Clientèle** (`clientele.py`) : à chaque pas d'ouverture, un nombre de clients anonymes tiré autour de l'affluence de l'heure (loi de Poisson), chacun avec un panier d'un à quatre articles selon le moment de la journée ; les habitués de la fiche viennent à leur heure avec leur panier et leurs propos du jour. Le flux ne dépend que de la date et de l'heure ; ce qui est vendu dépend du stock (un produit épuisé est une rupture).
- **Comptoir** : café à 09:30 et 16:30, verres d'eau, toilettes pendant un creux, Le Progrès, bavardage avec le buraliste, les Grosses Têtes à la radio, étal à remplir ou à resserrer. Entre deux clients, à peu près une fois sur deux, il s'occupe d'un rayon (`taches_de_fond`). Chaque pas note l'endroit de sa tâche (`poste` : bout de l'étal, rayons, vitrine réfrigérée, réserve, vitrine sur la rue) et les clients présents (`visiteurs` : qui, rayons où ils cherchent leurs articles, passage à la caisse).
- **Magasin** : pain livré chaque matin (invendus repris), grossiste le mardi et le vendredi selon le bon de commande du dimanche à la fermeture et du jeudi soir (chaque produit ramené à son stock cible), caisse vidée au coffre à midi et le soir ; le dimanche à la fermeture, tri des produits frais périmés, ménage et comptes de la semaine.
- **Lundi, jour de congé** : la boutique reste fermée ; il ne passe à la Croix-Rousse que pour prendre la recette au coffre de l'arrière-boutique, rideau baissé, et la déposer à la banque. Le reste de la journée : rosiers, bricolage, potager, cinéma avec Josiane.
- **Maison** : le soir, il prélève au magasin ce qui manque pour les repas de Josiane (menus de la fiche, avec leurs ingrédients) et ses propres provisions ; le dimanche midi, de quoi tenir jusqu'au déjeuner du mardi ; après une nuit trop courte, il oublie le cabas.
- **Soirées** : télévision écourtée par la fatigue, match du mercredi, belote du samedi, cinéma du lundi ; le dimanche, vote et randonnée dans les monts d'Or.

Aux pas où la journée de Thomas le fait entrer dans la boutique, Robert le sert : mêmes répliques (`data/monde/echanges.json`, y compris le conseil de film du samedi), mêmes achats, même paiement. Le match du mercredi (`data/monde/evenements.json`) est vécu aux mêmes minutes par les deux personnages.

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

### Perception et croyances

`perception.py` calcule à chaque pas éveillé ce que Thomas voit, entend et remarque (fiche, section `perception`). Ce qu'il croit est séparé de ce qui est réel : la simulation tient ses croyances sur l'emplacement de chaque objet, qui ne changent que par ses propres gestes ou par ce qu'il remarque.

- **Voir** : les pièces qu'il traverse et celle où il se tient, si elle est éclairée ou s'il y fait jour. Il remarque un objet avec une probabilité `attention × (0,5 + 0,5 × importance) × (1 − 0,4 × concentration)` (attention 0,5 dans la pièce où il se tient, 0,2 en passant), tirée de façon déterministe.
- **Remarquer** : un objet vu ailleurs que là où il le croyait, ou absent de là où il le croyait, corrige sa croyance et fait vivre l'événement `objet_deplace` (`objet_retrouve` quand il le revoit).
- **Entendre** : les appareils allumés à portée (la pièce, les pièces voisines ou tout le logement).
- **Rencontrer** : les personnes simulées du lieu (Robert à l'épicerie).

L'agent décide d'après ses croyances : chaque geste sur un objet part de là où il le croit. Si l'objet n'y est pas, il le prend là où il l'a remarqué ; sinon il le cherche, d'abord dans la pièce, puis dans les pièces les plus proches, deux par pas de 5 minutes ; introuvable après 25 minutes, il renonce et fait sans.

Sans perturbation, ses croyances restent égales à la réalité et la semaine est inchangée : seuls s'ajoutent les champs `perception` des pas.

```bash
# Rejouer la semaine avec un scénario de perturbations, puis la comparer à la semaine officielle
python3 outils/simuler_agent.py 2010-03-08 2010-03-14 --dossier data/scenarios/cles-deplacees --scenario data/scenarios/cles-deplacees.json
python3 outils/comparer_journees.py data/timelines/thomas-berthier/2010-03-09.json data/scenarios/cles-deplacees/2010-03-09.json
```

### Livres

Les livres à lire sont listés dans `regles.json` (section `lecture.livres`), dans l'ordre : objet de la fiche, titre, nombre de pages, page de départ, pensées de début et de fin. Il lit 5 pages par pas. Quand un livre est fini, il le range dans la bibliothèque du séjour à la séance de lecture suivante et prend le suivant. Le reste d'une plage de lecture, une fois le livre fini, devient de la musique.

### Fin de semaine

Le samedi et le dimanche n'ont pas de sonnerie : réveil naturel entre 07:30 et 08:30. Le plan de ces journées (ménage, sieste, sortie longue du dimanche, séances sur la montre du grand-père, planification de la semaine) est dans `regles.json`, sections `samedi` et `dimanche`.

Le résumé de chaque journée distingue les besoins passés sous le seuil d'alerte **éveillé** (à examiner) et **pendant le sommeil** (durée par besoin, attendu pour la soif la nuit).

## Habitant générique

`habitant.py` fait vivre n'importe quel habitant sans code qui lui soit propre, pour pouvoir peupler la ville. Un habitant, c'est sa fiche : besoins, logement et routines dont chaque étape nomme une action (`"activite"`, et `"avec"` pour les appareils d'ambiance comme la radio). Les actions sont décrites une fois pour toutes dans `data/monde/actions.json`, à la manière d'objets intelligents : où elles se font (un mot du mobilier ou du nom d'une pièce), posture, charge, besoins satisfaits, appareils, événements, phases (préparer puis manger), variantes (sieste si l'énergie est basse).

À chaque pas, il donne un score aux actions possibles et fait la meilleure :

| Action | Score |
|---|---|
| Étape de routine en cours (ancrage) | 1 |
| Besoin sous son seuil d'alerte (toilettes, soif, faim) | 1 + (seuil − valeur) / seuil : il s'interrompt un pas |
| Besoin sous le double de son seuil, au début d'une étape | 1 + 0,5 × (2 × seuil − valeur) / (2 × seuil) : il en profite avant de s'y mettre |

Le moteur calcule ensuite déplacements, lumière, besoins et émotions comme pour les autres agents. La nuit s'enchaîne d'elle-même : l'étape `coucher` éteint, l'endormissement dure selon l'état émotionnel, puis il dort jusqu'à la première étape du lendemain.

**Objets.** Une action du catalogue nomme les objets par leur rôle (`lunettes`, `cles`, `montre`, `tasse`…) ; la fiche dit quel objet tient ce rôle et où il se trouve dans chaque état (`porte`, `usage`… ; `rangement` est sa place de départ). `objets` le déplace au premier pas de l'action (il prend ses clés en sortant, les repose en rentrant) ; `tient` le garde pendant toute l'action et le repose dès que le pas suivant ne le demande plus : il pose ses lunettes pour aller aux toilettes et les remet en reprenant le travail. Une étape de routine peut ajouter les siens (la tenue de course le mardi matin). Chaque geste part de là où il croit l'objet ; s'il n'y est pas, il fait sans, et c'est noté.

**Provisions.** Un repas consomme le menu de la fiche (`menus_prevus`) : les ingrédients au début de la préparation, le plat préparé pour plusieurs repas (la marmite de soupe, quatre portions) et la portion au début du repas proprement dit. Une pause ou un petit creux prend ce que la fiche prévoit pour cet usage (`collations` : café, fruit, biscottes à défaut, chocolat du soir), en alternant les choix en stock d'un jour à l'autre. Il n'utilise que ce qu'il a : un ingrédient qui manque est noté dans les écarts, et une collation impossible ne nourrit pas.

**Approvisionnement.** La fiche dit où il s'approvisionne (`approvisionnement.commerce` : la fiche d'un commerçant) et ce qu'il veut avoir chez lui (`liste` : une cible à compléter, ou un seuil sous lequel il rachète). Sa liste y ajoute ce que demandent ses menus d'ici au prochain approvisionnement prévu par ses routines (au plus tard la fin de la semaine), puis les envies du jour. Une provision se trouve au catalogue du commerce sous son identifiant, ou sous celui que donne `magasin`, et une unité vendue en donne `par_unite` (ou la `quantite` du catalogue).

- **Chez un autre** (Thomas chez Robert) : l'action `courses` le fait sortir à pied. En partant, il passe aux toilettes ou boit un verre d'eau si le besoin passerait sous son seuil avant son retour (`anticipe`). Il note ce qui manque, prend sa veste, son sac, son portefeuille et ses clés, sort, descend l'escalier, marche (`approvisionnement.distance_m`), fait le tour des rayons, paie (espèces sous un montant s'il lui en reste assez, sinon carte), rentre et range. Les courses n'ont pas lieu si le commerce est fermé ou si rien ne manque.
- **Chez lui** (Robert dans sa boutique) : à une étape de routine marquée `approvisionne` (la fermeture du soir, le dimanche midi), il prélève sa liste sur le stock du magasin, dans la limite de ce qui reste.

**Son commerce.** Un habitant qui tient un commerce (section `commerce` de sa fiche) le fait vivre avec quatre actions du catalogue :

- `ouverture_boutique` (`livraison`) : le matin, une fois par jour d'ouverture, il reçoit les livraisons. Une livraison quotidienne (le pain) apporte les quantités du jour et reprend les invendus de la veille ; celle du grossiste, les jours prévus, ramène chaque produit non frais à son stock cible. Il met aussitôt de côté pour la maison ce que sa fiche prévoit (`approvisionnement.mis_de_cote` : la baguette de Robert).
- `tenir_boutique` (`service`) : à chaque pas, il sert les clients du flux déterministe de `clientele.py` (les mêmes que pour l'agent écrit à la main) avec le stock du magasin ; la recette va en caisse, sur le compte ou sur l'ardoise, les ruptures sont notées.
- `fermeture_boutique` (`caisse_au_coffre`) : les espèces au-delà du fond de caisse rejoignent le coffre.
- `banque` (`depot_coffre`) : la recette du coffre est déposée sur son compte.

Deux étapes de routine peuvent se recouvrir : la plus courte l'emporte, comme des courses prises sur le temps libre, et si elle n'a pas lieu, la plus longue reprend.

```bash
python3 outils/simuler_habitant.py 2010-03-08 2010-03-14 --dossier data/generique/thomas-berthier
python3 outils/comparer_journees.py data/references/thomas-berthier/2010-03-08.json data/generique/thomas-berthier/2010-03-08.json
```

Mesure sur Thomas, à partir de sa seule fiche (lundi, comparé à la journée de référence) : même pièce 91 % des pas, même lieu 100 %, même posture 88 %, mêmes appareils 76 % ; chaque objet à la même place 97 % du temps et chaque provision au même stock 98 % (mardi : 83 % et 95 % ; mercredi : 76 % et 92 %, `concordance_un_par_un` de `comparer_journees.py`). Restent les gestes propres à son travail (montres des clients sorties du coffre, ébauche d'axe au tour, marmite). Avec les courses du mardi, du jeudi et du samedi, comparé à la semaine officielle : même lieu 100 % les jours de semaine, chaque provision au même stock 89 à 98 % du lundi au samedi et 84 % le dimanche (76 % sans les courses) ; ses listes ressemblent à celles de l'agent écrit à la main (mardi : 4 pommes, 2 oranges et 3 bananes, contre 3 pommes et 3 bananes), les écarts venant des fruits mangés en plus. Sur la semaine, comparé à l'agent écrit à la main : 84 à 91 % de pièces identiques du lundi au vendredi, 68 à 72 % le week-end, dont les sorties (cinéma, vote, courses) ne sont pas encore dans les routines.

Robert vit lui aussi avec ce moteur, sans code propre : ses routines nomment leurs actions, et sa fiche dit où il gare la Kangoo sur chaque site (`voiture.stationnements`), la distance entre ses sites (`voiture.itineraires`) et le lieu de chaque site (`domicile.plan.lieux_des_sites`). Règles générales ajoutées pour lui : une pièce se cherche d'abord sur le site où il se trouve, un besoin pressant ne l'envoie que dans une pièce de ce site, il éteint tout en quittant un site, et un événement que sa fiche ne connaît pas n'a pas d'effet sur lui. Mardi, comparé à sa journée de référence : même pièce 90 %, même lieu 99 %, même posture 91 %, mêmes appareils 88 %, chaque provision au même stock 88 % (ses menus avaient déjà leurs ingrédients) ; il prélève au magasin pour la maison en fermant (œufs, jambon, bière…) : comparé à la semaine officielle, chaque provision au même stock 86 à 90 % du mardi au samedi (65 à 88 % sans les prélèvements). Sa boutique vit aussi : livraisons, clients, caisse et coffre. Mardi, il sert 109 clients (211 lignes de vente) contre 115 (220 lignes) dans la semaine officielle ; le coffre finit la semaine à 1 562 € contre 1 623 €. Chaque produit du magasin est au même stock 49 à 89 % du temps selon le jour (environ 10 % sans la boutique), chaque provision de la maison 80 à 97 %, et aucun repas ne manque plus de pain. L'écart vient surtout des visites de Thomas, que l'habitant générique ne connaît pas encore, et des produits périmés jetés le dimanche, pas encore gérés.

```bash
python3 outils/simuler_habitant.py 2010-03-08 2010-03-14 --personnage robert-chazal --dossier data/generique/robert-chazal
```

## Quartier : plusieurs habitants ensemble

`quartier.py` fait vivre ensemble, pas à pas, n'importe quels habitants : chacun décide de son pas, le quartier ajoute les rencontres et les conversations, puis chaque pas est calculé. Les fiches sont chargées par `fiches.py`, qui les complète avec le monde (`data/monde/`, voir « Créer un nouvel habitant » dans `data/README.md`). Les règles sont générales ; leurs valeurs viennent de `data/monde/interactions.json`, par type de relation, et chaque fiche peut les remplacer dans `relations`.

- **Ensemble** : deux habitants éveillés dans la même pièce du même logement (repère commun : logement et pièce, quelle que soit la fiche qui la décrit), le même lieu public ou le même véhicule, sans action intime en cours. Chacun gagne le contact social de la relation ; le premier pas fait vivre l'événement de rencontre (`moment_proche`, `rencontre_ami`, `rencontre_voisin`…). Une personne simulée inconnue est remarquée (`croise`). « Manger seul » n'est vécu que si l'on mange seul.
- **Moment prévu ensemble** (`avec_personnes`) : si la personne n'est venue ni au premier ni au deuxième pas, l'absence est remarquée et vécue.
- **Conversation** : entre deux habitants ensemble et disponibles, selon la probabilité de la relation, au plus une toutes les 30 minutes par paire. Le plus extraverti parle (sauf tirage). Sujet : une préoccupation de la semaine, confiée à un proche mais jamais à la personne qu'elle concerne ; ce qu'il a fait sans l'autre, à un proche, un voisin ou un collègue mais pas à un commerçant ni à un client (ce qui est banal ne se raconte pas) ; l'activité partagée (`sujet` dans le catalogue : le repas, la partie, le match…) ; une banalité. Les textes viennent de modèles ; l'auditeur répond selon son agréabilité et **retient** ce qu'on lui a dit (mémoire `appris`, gardée d'un jour à l'autre).
- **À pied d'un logement à l'autre** : il sort par l'accès de son logement (la rue) et entre par celui du logement où il va. Deux habitants en chemin ne sont pas ensemble pour autant : chacun suit son propre trajet.
- **Commerce** : un client entre dans la salle où le commerçant sert (`commerce.salle` : la boutique de Robert) ; quand il achète dans le commerce d'un autre habitant du quartier, c'est ce commerçant qui le sert : la vente sort du stock de son magasin, dans la limite de ce qui reste en rayon (sinon le client fait sans), et la recette va dans sa caisse ou sur son compte.

Exemple : Robert, Josiane et leurs voisins Gérard et Monique Morel (fiches minimales). Le samedi soir, les quatre jouent à la belote chez les Chazal ; Josiane et Monique se retrouvent au marché ; le dimanche, les deux couples se croisent au bureau de vote sans l'avoir prévu. Robert confie à Gérard et à Monique qu'il cherche un cadeau pour l'anniversaire de mariage, jamais à Josiane ; Josiane confie à Monique qu'elle se demande s'il y pensera : Monique sait les deux.

Thomas y vit aussi, avec sa fiche complète : le mardi, le jeudi et le samedi, il retrouve Robert à l'épicerie (rencontre, quelques mots sur le quartier ou le temps), et Robert lui vend ses fruits, son comté, son pain de campagne sur le stock de sa boutique. Avec ces ventes, le stock du magasin de Robert se rapproche de sa semaine officielle (chaque produit au même stock 53 à 90 % du temps selon le jour, contre 49 à 89 % sans Thomas) ; le coffre finit la semaine à 1 574 € (1 623 € dans la semaine officielle).

Limite : chacun garde son propre état du monde (lumières, appareils, objets, provisions) ; les logements ne sont pas encore un état partagé. Seul le stock d'un commerce est commun, par les ventes du commerçant.

```bash
python3 outils/simuler_quartier.py 2010-03-08 2010-03-14 --personnages thomas-berthier robert-chazal josiane-chazal gerard-morel monique-morel --dossier data/quartier
```

## Le voyageur et la divergence

Le monde de référence est le quartier (`data/quartier`) ; le monde joué est le même quartier rejoué avec les interventions du voyageur (`voyageur.py`, scénarios dans `data/voyageur/`). Pour les habitants, le voyageur n'est qu'un passant. À chaque pas, le quartier lui demande s'il retient un habitant (avant que celui-ci décide : il reste où il est, et ce qu'il devait faire n'est pas fait ; des courses qui auraient dû commencer sont abandonnées), puis, une fois les décisions prises, s'il achète dans un commerce ou parle à quelqu'un ; un objet qu'il déplace change de place avant que l'habitant décide, sans que celui-ci le sache.

**Anachronismes.** Le voyageur porte des objets (`porte`) et peut s'en servir pendant une intervention (`utilise`) ; `data/monde/epoque.json` dit ce qui existe en 2010. Pendant chaque intervention, il est quelque part : auprès de l'habitant qu'il retient ou à qui il parle, dans la salle du commerce où il achète, dans le lieu où il passe. Chaque habitant éveillé au même endroit peut remarquer un objet apparu après 2010, avec une probabilité qui tient à sa visibilité (plus grande s'il s'en sert), à l'attention de l'habitant (relative à l'attention ordinaire), à sa concentration, et au face-à-face (tirage déterministe). Une anomalie remarquée fait vivre l'événement `anachronisme_remarque`, reste en mémoire (`anomalies`) et devient le premier sujet de conversation après les confidences : on la raconte à tout le monde, et qui l'a entendue la répète. Un téléphone à clapet ou un billet de la première série ne surprend personne.

`divergence.py` compare les deux mondes pas à pas, habitant par habitant, selon les deux niveaux de `CONCEPTION.md` :

| Niveau | Ce qui est comparé | Traitement |
|---|---|---|
| Faits | Endroit (lieu et pièce), activité, personnes avec qui il est, place de chaque objet, achats, ce qu'il a appris (qui le lui a dit, et quoi), les anachronismes qu'il a remarqués ou dont il a entendu parler | Comptés : chaque fait différent une fois par heure, même s'il dure |
| Détails | Besoins, émotions, quantités en stock (maison et magasin), argent | Mesurés à la fin, tolérés |

Un habitant touché sans être visé par une intervention ni témoin d'un anachronisme l'est par cascade ; le premier fait différent de chacun montre la propagation.

**Chaîne des causes.** Un fait différent qui dure forme un épisode, et chaque épisode reçoit, quand il commence, sa cause la plus directe : l'intervention du voyageur qui le vise (il le retient, déplace son objet, lui dit quelque chose) ; pour une rencontre manquée, ce qui a changé pour l'autre à ce moment (son endroit, son activité), sinon pour lui-même ; pour ce qu'on apprend ou pas de quelqu'un, la dernière rencontre différente avec lui ; pour un achat, sa journée changée ou un achat du voyageur sur ce produit ; pour un objet, ce qu'il était en train de faire ; sinon, le premier changement de sa journée dont il découle, « par ses besoins décalés » si ses besoins diffèrent à ce moment. `DIVERGENCE.md` en dessine l'arbre, du voyageur au dernier fait. Par exemple, pour la belote :

```
Le voyageur, samedi 20:35 — retient Robert 30 minutes
  Robert 20:45 — lieu : séjour → cuisine
    Gérard, Josiane, Monique 20:45 — rencontre : sans Robert
      Josiane 21:40 — apprend : retenu par un passant (Robert le lui raconte)
    Robert 20:45 — rencontre : sans Gérard, Josiane, Monique
      Robert 20:55 — ne sait pas : son genou… (Monique ne le lui a pas confié)
    Robert, dimanche 07:00 — activité : passe aux toilettes à un autre moment (par ses besoins décalés)
```

Les causes se déduisent des deux mondes, sans trace gardée par le moteur : c'est une reconstruction, qui marque « lien supposé » un fait dont la cause n'a pas pu être trouvée. Le verdict : aucune divergence ; absorbée (plus aucun fait différent à la fin de la période) ; persistante ; en cascade ; paradoxe, si la divergence touche au moins 3 habitants ou compte au moins 40 faits différents dans une heure (`data/monde/paradoxe.json`).

```bash
# Le monde de référence (une fois), puis chaque scénario
python3 outils/simuler_quartier.py 2010-03-08 2010-03-14 --personnages thomas-berthier robert-chazal josiane-chazal gerard-morel monique-morel --dossier data/quartier
python3 outils/simuler_voyageur.py data/voyageur/courses-manquees.json
```

Le scénario `temoin` (aucune intervention) vérifie que le monde joué reproduit exactement le monde de référence. Résultats des scénarios dans `data/README.md` (section « Le voyageur »).

## Vue fil de fer

Deux pages, à ouvrir dans un navigateur : `vue/index.html`, la semaine en fil de fer (ci-dessous), et `vue/divergence.html`, le voyageur.

**Le voyageur** (`vue/divergence.html`) : on choisit un scénario (pastille de la couleur du verdict) ; une frise montre, habitant par habitant, chaque fait qui diffère du monde de référence, en bandes par genre (endroit et activité, rencontres, objets et achats, ce qu'on a appris, anachronismes), avec les interventions du voyageur en traits rouges, sur six heures autour de l'instant, un jour ou la semaine. En cliquant sur la frise (ou avec les flèches), on choisit l'instant : pour chaque habitant, ce qu'il fait dans le monde de référence et, s'il diffère, dans le monde joué, avec les faits en cours. La chaîne des causes est un arbre dont chaque fait mène à son instant sur la frise. Le scénario affiché se retrouve dans l'adresse (`divergence.html#scenario=belote`).

```bash
# Recalculer les données de la page du voyageur (rejoue un scénario dont le monde joué manque)
python3 outils/exporter_divergence.py
```

L'export (`vue/divergence.js`) écrit le monde de référence une seule fois et, pour chaque scénario, seulement les pas qui en diffèrent, les faits (épisodes) et leurs causes.

### La semaine en fil de fer

La semaine se rejoue dans une vue isométrique fil de fer (`vue/index.html`, à ouvrir dans un navigateur), à plusieurs échelles, les mêmes pour les deux personnages : le logement (l'appartement de Thomas, la boutique ou la maison de Robert), l'immeuble (ou la maison), la rue du lieu où se trouve le personnage suivi (pour Thomas, de chez lui à l'épicerie ; pour Robert, la Grande-Rue autour de l'épicerie, avec la place et la banque, ou la rue des Glycines), le parcours de course (pentes et quais de Saône), les sorties à pied de Thomas (vers le cinéma par la montée de la Boucle, le boulevard jusqu'à la mairie du 4e et au Gros Caillou), et pour Robert le trajet en Kangoo (Croix-Rousse, Rhône, Villeurbanne), le cinéma de la Cité internationale, l'école où il vote et les monts d'Or. On choisit le personnage suivi (Thomas ou Robert) ; l'autre reste visible. Le panneau donne l'état de chaque pas : activité, pensée, besoins, émotions, objets portés, argent, lumières et appareils.

La lecture va de 5 minutes simulées par seconde à 4 heures par seconde, ou en **temps réel** (1 s = 1 s) : les actions restent celles des pas de 5 minutes ; l'horloge avance à la seconde, un déplacement dans un logement se fait au pas (1,3 m/s) puis le personnage reste à son poste, et un trajet dehors (marche, course, voiture) s'étale sur tout le pas. Les pièces de chaque logement portent leur nom, y compris sur un écran de téléphone.

Pendant les heures d'ouverture, la boutique s'anime pas par pas : les clients de la clientèle simulée (sans fiche, dessinés en gris, les habitués un peu plus nettement) entrent par la porte, font le tour des rayons de leurs articles (30 à 70 secondes devant chacun), passent à l'une des deux places libres de la caisse (30 à 60 secondes) et ressortent ; Robert reste à l'endroit de sa tâche et rejoint le comptoir quand un client vient payer, puis y retourne. Ces allées et venues sont calculées à l'export, de façon déterministe, en images-clés dans le pas (au pas de 1,3 m/s en temps réel). À l'arrêt sur un pas, la boutique est montrée au milieu du pas, avec ses clients.

```bash
# Recalculer les données de la vue après une génération de journées ou une modification du plan
python3 outils/exporter_vue.py
```

L'export lit la géométrie du monde (`data/monde/croix-rousse.json`), les fiches des personnages qui y ont un logement et toutes leurs journées. Tout est exprimé dans un seul repère, en mètres. Il calcule :
- le trajet de chaque personnage à chaque pas, porte par porte, par les escaliers (avec le détour par le local poubelles), puis dans les rues : courses à l'épicerie, descente des pentes, aller-retour le long de la Saône, remontée ; les trajets en voiture et à pied décrits dans `trajets_personnages` (pour Thomas, ses sorties à pied ; pour Robert, ses trajets entre ses deux lieux et ses sorties), un pas étant rattaché à un itinéraire par son activité ou par sa rue, la position suivant la part du trajet faite ;
- l'altitude de chaque bâtiment et des rues d'après le relief (plateau, pentes vers la Saône et le Rhône, monts d'Or) ;
- la position en 3D de chaque emplacement d'objet ;
- les immeubles ordinaires le long des rues et les arbres, générés de façon déterministe.

Il s'arrête si une liaison du plan d'une fiche n'a pas de porte ou si une pièce n'a pas de rectangle. Il affiche les distances entre pièces mesurées sur le plan, à comparer avec celles des fiches.
