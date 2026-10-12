"""Lundi 8 mars 2010 — contenu rédigé de la journée de Robert Chazal.

Jour de fermeture de l'épicerie. Robert dort sans réveil, déjeune avec
Josiane avant qu'elle parte au cabinet, puis va à la boutique en Kangoo :
dépôt de la recette de la semaine au coffre de la banque, grand ménage,
comptes, bon de commande du grossiste pour mardi. L'après-midi, sieste,
potager et garage ; le soir, mots croisés, dîner et télévision avec Josiane.
"""
from commun import ALLER_LENT, BOUTIQUE, RETOUR_LENT, TRAJET, Magasin, en_voiture, euros, ingredients, mvs, nuit
from moteur import Journee, c, marche, off, on, onoff, p

KANGOO = "Kangoo"


def rediger(etat):
    j = Journee("2010-03-08", "lundi", extinction="23:20")
    import json, os
    fiche = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "personnages", "robert-chazal.json")))
    mag = Magasin(fiche, etat, "2010-03-08", "lundi")

    # ------------------------------------------------------------ nuit
    # Endormi à 22:30 le dimanche : cycles de 90 minutes à partir de 22:30.
    j.seg("00:00", "Nuit de dimanche à lundi", "chambre", "sommeil", "sommeil", "sommeil", "allongé", nuit([
        ("00:00", "00:20", "léger", None, None),
        ("00:20", "01:15", "profond", None, None),
        ("01:15", "01:30", "léger", None, None),
        ("01:30", "01:55", "paradoxal", "La boutique est pleine ; tout le monde parle en même temps et le tiroir de la caisse refuse de s'ouvrir.", "reve_inquiet"),
        ("01:55", "02:10", "léger", None, None),
        ("02:10", "02:50", "profond", None, None),
        ("02:50", "03:10", "léger", None, None),
        ("03:10", "03:35", "paradoxal", "Le bal de la Croix-Rousse, en 1974. Josiane porte sa robe à pois et se moque de ses chaussures neuves.", "reve_souvenir"),
        ("03:35", "03:40", "micro-éveil", None, None),
        ("03:40", "04:00", "léger", None, None),
        ("04:00", "04:25", "profond", None, None),
        ("04:25", "04:55", "léger", None, None),
        ("04:55", "05:25", "paradoxal", "Lucas choisit des bonbons un par un dans les bocaux, et les bocaux ne se vident jamais.", None),
        ("05:25", "05:55", "léger", None, None),
        ("05:55", "06:05", "profond", None, None),
        ("06:05", "06:45", "léger", None, None),
        ("06:45", "06:50", "micro-éveil", None, None, "Josiane se lève sans bruit ; il entend la porte de la salle de bain, se rendort."),
        ("06:50", "07:15", "léger", None, None),
    ]))

    # ------------------------------------------------------------ matin
    j.seg("07:15", "Réveil sans sonnerie", "chambre", "rt-lundi", "eveille", "repos", "assis", [
        p("Se réveille de lui-même. Le côté de Josiane est vide ; en bas, la radio et l'odeur du café. Attache sa Seiko au poignet, "
          "remonte ses lunettes sur son front.", "Lundi. Pas de réveil, pas de rideau à lever. Juste la banque et le ménage.",
          objets=mvs([("obj-montre", "chambre / table de chevet de Robert", "poignet gauche"),
                      ("obj-lunettes", "chambre / table de chevet de Robert", "sur son front")])),
    ])
    j.seg("07:20", "Toilette", "salle-de-bain", "rt-lundi", "eveille", "simple", "debout", [
        p("Passe aux toilettes de la salle de bain.", None, effets={"toilettes": "vide"}),
        p("Prend une douche.", "L'eau chaude sur le dos. Ça le décoince.", effets={"hygiene": 75}, ev=["plaisir_simple"]),
        p("Se rase devant le miroir embué.", None, charge="precision"),
        p("S'habille dans la chambre : chemise à carreaux, pantalon de velours, vieux pull pour le ménage.", None, piece="chambre"),
    ])
    j.seg("07:40", "Petit-déjeuner avec Josiane", "cuisine", "rt-lundi", "eveille", "repos", "assis", [
        p("Descend à la cuisine. Josiane a fait le café et beurré ses tartines. Il s'assoit en face d'elle, la radio en fond.",
          "Trente-quatre ans qu'elle me fait mes tartines le lundi.", ev=["moment_josiane", "plaisir_simple"], radio=True,
          app=on("radio-cuisine"), effets={"cafe": True, "social": 1.0}, consommation=ingredients(fiche, None, "petit_dejeuner")),
        p("Mange ses tartines, boit son café sucré, avale son comprimé pour la tension avec un verre d'eau. Josiane parle de sa sœur.",
          None, radio=True, effets={"faim": 40, "soif": 30, "social": 1.0}),
        p("Josiane enfile son manteau : « À midi. Fais pas le ménage comme un sauvage, avec ton dos. » Elle part à pied au cabinet.",
          "Comme un sauvage. Je le fais comme il faut, c'est tout.", radio=True, effets={"social": 1.0}),
    ])
    j.seg("07:55", "Départ pour la boutique", "garage", "rt-lundi", "eveille", "simple", "debout", [
        p("Éteint la radio, rince les bols. Prend sa veste, ses clés, celles de la Kangoo et son portefeuille dans le vide-poche, "
          "passe au garage et ouvre la porte basculante.", None, app=off("radio-cuisine"), via=["cuisine"],
          objets=mvs([("obj-veste", "entree / portemanteau", "porté"), ("obj-cles", "entree / vide-poche", "poche de la veste"),
                      ("obj-cles-kangoo", "entree / vide-poche", "dans sa main"), ("obj-portefeuille", "entree / vide-poche", "poche de la veste")])),
    ])
    j.seg("08:00", "Route vers la Croix-Rousse", KANGOO, "rt-lundi", "eveille", "conduite", "assis", en_voiture([
        "Sort la Kangoo, referme la porte basculante, éteint la lumière du garage par la vitre. Rue des Glycines, puis le cours Émile-Zola, déjà chargé.",
        "Cours Émile-Zola au pas, de feu en feu, derrière un bus.",
        "Boulevard de Stalingrad, puis le pont Winston-Churchill. Le Rhône est gris.",
        "Monte la montée de la Boucle en seconde, longe le boulevard de la Croix-Rousse et entre dans la cour de l'épicerie.",
    ], ALLER_LENT, pensees=["Le lundi, tout Villeurbanne part travailler en même temps que moi.", None, None, None],
        ev=[["embouteillage"], None, None, None],
        extra={0: {"objets": mvs([("obj-kangoo", "garage / place de la Kangoo", "en route"), ("obj-cles-kangoo", "dans sa main", "contact de la Kangoo")]),
                   "app": off("lumiere-garage")}}), lieu=TRAJET)

    # ------------------------------------------------------------ banque
    j.seg("08:20", "Recette de la semaine", "arriere-boutique", "rt-lundi", "eveille", "precision", "debout", [
        p("Gare la Kangoo à sa place dans la cour, entre par la porte de derrière. Dans l'arrière-boutique, ouvre le coffre, recompte la recette "
          f"de la semaine passée, {euros(etat['argent']['coffre'])}, et la glisse dans une pochette de dépôt de la banque avec le bordereau rempli.",
          "Mille cent quatre-vingt-quatre euros soixante en liquide. L'an dernier à la même époque, c'était plus.",
          retour="cour-epicerie", ev=["constat_chiffre"],
          objets=mvs([("obj-kangoo", "en route", "cour-epicerie / place louée"), ("obj-cles-kangoo", "contact de la Kangoo", "poche de la veste")]),
          nouveaux_objets=[{"id": "obj-pochette-depot", "nom": "Pochette de dépôt de la banque (recette en espèces de la semaine)", "position": "dans sa main"}]),
    ], lieu=BOUTIQUE)
    j.seg("08:25", "Dépôt au coffre de la banque", "boulevard de la Croix-Rousse", "rt-lundi", "eveille", "simple", "en marche", [
        p("Ressort par la cour avec la pochette sous le bras, remonte la Grande-Rue jusqu'au boulevard.", None,
          sortie="cour-epicerie", parcours=[marche(300)], lieu="exterieur"),
        p("Devant l'agence fermée, ouvre la trappe du coffre de dépôt avec sa clé, y glisse la pochette et referme.",
          "Voilà. Elle est à la banque, plus chez moi.", piece="coffre de dépôt de la banque", lieu="banque", posture="debout",
          ev=["depot_recette"], argent={"coffre": -etat["argent"]["coffre"], "compte": etat["argent"]["coffre"]},
          objets=mvs([("obj-pochette-depot", "dans sa main", "banque / coffre de dépôt")])),
        p("Redescend la Grande-Rue. M. Garnier, le buraliste d'à côté, lève son rideau ; trois mots sur le tiercé et sur Madrid.",
          "Garnier dit 2-0 pour le Real. Il dit toujours le pire.", parcours=[marche(300)], lieu="exterieur",
          piece="Grande-Rue de la Croix-Rousse", ev=["bavardage_voisin"], effets={"social": 2}),
    ])
    j.seg("08:40", "Blouse", "arriere-boutique", "rt-lundi", "eveille", "simple", "debout", [
        p("Rentre par la cour, accroche sa veste à la patère, enfile sa blouse grise, met ses clés dans la poche.", None, retour="cour-epicerie",
          objets=mvs([("obj-veste", "porté", "arriere-boutique / patère"), ("obj-blouse", "arriere-boutique / patère", "porté"),
                      ("obj-cles", "poche de la veste", "poche de la blouse"), ("obj-cles-kangoo", "poche de la veste", "poche de la blouse")])),
    ], lieu=BOUTIQUE)

    # ------------------------------------------------------------ ménage
    perimes = {"yaourts": 2, "salade": 1}
    reprise = mag.reprendre(perimes, "date dépassée ou abîmé, jeté")
    j.seg("08:45", "Grand ménage de la boutique", "boutique", "rt-lundi", "effort", "simple", "debout", [
        p("Allume la boutique, rideau baissé, et la radio sur RTL. Sort de la réserve le seau, la serpillière et le balai.", None,
          via=["reserve"], app=on("lumiere-boutique", "radio-boutique"), radio=True, mode="travail"),
        p("Balaie la boutique, du fond vers la porte.", None, radio=True, ev=["effort_physique"]),
        p("Balaie sous les rayons, ramasse un ticket de loto et une pièce de dix centimes.", "Dix centimes. Le loto, je le garde pas.", radio=True),
        p("Remplit le seau à l'évier de l'arrière-boutique et lave le sol.", None, via=["arriere-boutique"], radio=True, ev=["effort_physique"]),
        p("Lave le sol, à genoux dans les coins.", "Le dos. Bon. Encore deux coins.", radio=True, ev=["mal_de_dos"]),
        p("Vide le seau, rince la serpillière, laisse sécher le sol.", None, via=["arriere-boutique"], radio=True),
        p("Trie les produits frais de la vitrine réfrigérée : deux packs de yaourts au-delà de leur date et une laitue fanée partent à la poubelle.",
          "Deux packs de yaourts pour rien. Faut que je commande moins.", radio=True, mode="travail", reprises=reprise),
        p("Vide la vitrine réfrigérée et range les produits dans la chambre froide de la réserve.", None, via=["reserve"], radio=True),
        p("Lave les clayettes de la vitrine réfrigérée à l'eau savonneuse.", None, radio=True),
        p("Essuie les clayettes, remet tout en place, les dates les plus courtes devant.", None, via=["reserve"], radio=True, mode="travail"),
        p("Monte sur l'escabeau et dépoussière les rayons du haut.", None, radio=True, ev=["effort_physique"]),
        p("Dépoussière les conserves une par une.", "Les haricots verts, personne n'en prend. J'en commande toujours trop.", radio=True),
    ])
    j.seg("09:45", "Café de dix heures moins le quart", "boutique", "rt-lundi", "eveille", "simple", "debout", [
        p("Passe aux toilettes du fond, puis se fait un café dans l'arrière-boutique et le boit debout, la tasse de Lucas à la main.",
          "« Meilleur papi. » Il a écrit le « p » à l'envers, sur la carte.", via=["wc-boutique", "arriere-boutique"], radio=True,
          effets={"toilettes": "vide", "cafe": True, "soif": 15}, ev=["plaisir_simple", "pensee_claire"], consommation=[c("cafe_boutique", 7)],
          app=onoff(["cafetiere-boutique"], ["cafetiere-boutique"])),
    ])
    j.seg("09:50", "Grand ménage de la boutique", "boutique", "rt-lundi", "effort", "simple", "debout", [
        p("Nettoie l'étal des fruits et légumes, jette les feuilles et la terre.", None, radio=True),
        p("Lave la porte vitrée et l'intérieur de la vitrine.", None, radio=True),
        p("Lève le rideau à mi-hauteur pour laver la vitrine côté rue.", None, radio=True, via=["trottoir"]),
        p("Lave la vitrine côté rue, sur le trottoir encore à l'ombre.", "Les gens passent et regardent dedans. Fermé, mesdames, c'est lundi.",
          radio=True, piece="trottoir"),
        p("Rabaisse le rideau. Essuie le comptoir et la caisse.", None, radio=True, mode="travail"),
        p("Range la réserve : aplatit les cartons vides et les sort dans la cour.", None, via=["reserve", "cour-epicerie"], radio=True),
        p("Remet les cagettes vides en pile pour le grossiste.", None, piece="reserve", radio=True),
        p("Passe la serpillière dans la réserve.", None, piece="reserve", radio=True, ev=["effort_physique"]),
    ])

    # ------------------------------------------------------------ comptes
    j.seg("10:30", "Comptes de la semaine", "arriere-boutique", "rt-lundi", "travail", "precision", "assis", [
        p("Éteint la radio et la boutique, s'installe au bureau de l'arrière-boutique avec le cahier des comptes et descend ses lunettes sur son nez.",
          None, app=off("radio-boutique", "lumiere-boutique"), objets=mvs([("obj-lunettes", "sur son front", "sur son nez")]), via=["boutique"]),
        p("Recopie les recettes de la semaine dernière, jour par jour.", "Mardi 312, mercredi 295, jeudi 288… Samedi, heureusement."),
        p("Additionne : mille neuf cent quarante euros, cartes comprises.", "Mille neuf cent quarante. Avant la supérette, je faisais deux mille trois cents.",
          ev=["constat_chiffre"]),
        p("Classe les factures du grossiste et de la boulangerie."),
        p("Vérifie la facture du grossiste ligne par ligne.", "Le lait a encore pris deux centimes. Je peux pas tout répercuter."),
        p("Calcule le loyer et les charges du mois.", None),
        p("Fait le total du carnet des ardoises : quarante-six euros trente, dont trente-huit de M. Rey qu'il ne reverra pas.",
          "Rey. Parti à Vénissieux sans régler. Tant pis, c'était un brave homme.", via=["boutique"]),
        p("Compare avec mars de l'an dernier, page par page.", None),
        p("Range les factures dans le classeur pour le comptable.", None),
        p("Referme le cahier des comptes et remonte ses lunettes sur son front.", "Bon. Ça va bien comme ça. On tient.",
          ev=["comptes_faits"], objets=mvs([("obj-lunettes", "sur son nez", "sur son front")])),
    ], lieu=BOUTIQUE)

    # ------------------------------------------------------------ bon de commande
    cabas = [mag.pour_maison("pommes_de_terre", 1), mag.pour_maison("carottes", 1), mag.pour_maison("salade", 1)]
    commande = mag.commande()
    j.seg("11:20", "Bon de commande du grossiste", "reserve", "rt-lundi", "travail", "simple", "debout", [
        p("Compte les cartons et les packs dans la réserve, le carnet de bons de commande à la main.", None),
        p("Boit un grand verre d'eau à l'évier de l'arrière-boutique, puis compte les rayons de la boutique : conserves, pâtes, riz, café.", None,
          piece="boutique", via=["arriere-boutique"], app=on("lumiere-boutique"), effets={"soif": 25}),
        p("Remplit d'abord le cabas de la boutique pour Josiane : un sac de pommes de terre, un sachet de carottes pour la soupe de ce soir et "
          "une laitue pour demain midi. Puis compte les fruits et légumes de l'étal et la vitrine réfrigérée.",
          "Les carottes, elle me l'a dit trois fois. Je les ai.", piece="boutique", prelevements=cabas,
          objets=mvs([("obj-cabas-boutique", "arriere-boutique / patère", "dans sa main")])),
        p("S'assoit au bureau et remplit le bon de commande pour demain, les lunettes sur le nez : "
          f"{mag.texte(commande, limite=5)}.", None, piece="arriere-boutique", posture="assis",
          charge="precision", app=off("lumiere-boutique"), objets=mvs([("obj-lunettes", "sur son front", "sur son nez")])),
        p(f"Termine le bon de commande : {len(commande)} lignes pour la livraison de demain, 6 h 40. Le pose sur le bureau, sous l'agrafeuse.",
          "Avec ça, on tient jusqu'à vendredi.", piece="arriere-boutique", posture="assis", charge="precision",
          objets=mvs([("obj-lunettes", "sur son nez", "sur son front")])),
        p("Range le bureau, vérifie la porte de la cour et le coffre.", "Voilà le lundi fait. Plus que le cinéma, ce soir.", piece="arriere-boutique"),
    ], lieu=BOUTIQUE)

    # ------------------------------------------------------------ midi
    j.seg("11:50", "Retour à la maison", KANGOO, "rt-lundi", "eveille", "conduite", "assis", en_voiture([
        "Raccroche sa blouse, remet sa veste, éteint, ferme la porte de derrière et pose le cabas sur le siège passager. Sort la Kangoo de la cour "
        "et descend la montée de la Boucle.",
        "Traverse le Rhône par le pont Winston-Churchill.",
        "Boulevard de Stalingrad, puis le cours Émile-Zola, au pas derrière une camionnette.",
        "Rue des Glycines. Ouvre la porte basculante et rentre la Kangoo au garage.",
    ], RETOUR_LENT, pensees=[None, "Le Rhône. Quarante ans que je le traverse.", None, None],
        ev=[None, ["conduite_tranquille"], ["embouteillage"], None],
        extra={0: {"sortie": "cour-epicerie", "objets": mvs([("obj-blouse", "porté", "arriere-boutique / patère"),
                                                             ("obj-veste", "arriere-boutique / patère", "porté"),
                                                             ("obj-cles", "poche de la blouse", "poche de la veste"),
                                                             ("obj-cles-kangoo", "poche de la blouse", "contact de la Kangoo"),
                                                             ("obj-kangoo", "cour-epicerie / place louée", "en route")])}}), lieu=TRAJET)
    j.seg("12:10", "Déjeuner avec Josiane", "cuisine", "rt-repas", "eveille", "repos", "assis", [
        p("Entre par la porte du garage, pose les légumes sur la table de la cuisine, accroche sa veste et le cabas vide au portemanteau pour ne pas "
          "l'oublier demain, pose ses clés et son portefeuille dans le vide-poche. Josiane rentre à pied du cabinet au même moment, Le Progrès "
          "sous le bras ; elle met le gratin de la veille au four.", None, retour="garage", posture="debout", effets={"social": 1.0},
          objets=mvs([("obj-kangoo", "en route", "garage / place de la Kangoo"), ("obj-cles-kangoo", "contact de la Kangoo", "entree / vide-poche"),
                      ("obj-cles", "poche de la veste", "entree / vide-poche"), ("obj-portefeuille", "poche de la veste", "entree / vide-poche"),
                      ("obj-veste", "porté", "entree / portemanteau"), ("obj-cabas-boutique", "dans sa main", "entree / portemanteau")]),
          nouveaux_objets=[{"id": "obj-progres-0308", "nom": "Le Progrès du lundi 8 mars 2010", "position": "cuisine / table"}]),
        p("Met la table pendant que les côtes de porc grillent. Josiane raconte le cabinet : le docteur est en retard sur tout.", None,
          posture="debout", charge="simple", effets={"social": 1.0}),
        p("Se lave les mains et boit un verre d'eau.", None, posture="debout", effets={"soif": 20, "hygiene": 10}),
        p("Mangent le gratin dauphinois et les côtes de porc.", "Son gratin. Personne le fait comme elle.", ev=["moment_josiane", "plaisir_simple"],
          effets={"faim": 55, "social": 1.0}, consommation=ingredients(fiche, "lundi", "dejeuner")),
        p("Lui raconte la banque, le ménage, les yaourts périmés.", None, effets={"social": 1.0}),
        p("Josiane parle de Claire : elle a appelé hier soir, Emma a une otite.", "Une otite. À trois ans, ça passe. Faudrait qu'on y aille, à Grenoble.",
          ev=["pensee_claire"], effets={"social": 1.0}),
        p("Josiane propose le cinéma ce soir : le dernier Polanski passe à la Cité internationale.", "Polanski. Bon. Si elle y tient. Je dormirai mardi.",
          effets={"social": 1.0}, ev=["anticipation_plaisir"]),
        p("Josiane parle de leurs trente-quatre ans de mariage, le 16 : « Tu y as pensé, au moins ? »",
          "Le 16. Mardi prochain. J'ai rien, évidemment.", ev=["anniversaire_mariage"], effets={"social": 1.0}),
        p("Il dit que oui. Elle rit, elle ne le croit pas.", None, effets={"social": 1.0}, ev=["rire"]),
        p("Se fait un café à la cafetière électrique.", None, posture="debout", charge="cuisine", effets={"cafe": True, "soif": 10},
          app=onoff(["cafetiere-maison"], ["cafetiere-maison"]), consommation=[c("cafe_moulu", 7)]),
        p("Essuie la vaisselle et la range pendant que Josiane lave.", None, posture="debout", charge="simple", effets={"social": 1.0}),
    ])
    j.seg("13:05", "Le Progrès", "sejour", "rt-repos", "lecture", "lecture", "assis", [
        p("S'installe dans son fauteuil avec Le Progrès, les lunettes sur le nez : la neige à Perpignan, les régionales de dimanche.", None,
          objets=mvs([("obj-progres-0308", "cuisine / table", "sejour / dans sa main"), ("obj-lunettes", "sur son front", "sur son nez")]),
          ev=["lecture_journal"]),
        p("Lit la page de l'OL : deux pages sur Madrid.", "Mercredi. Le Bernabéu. Faut y croire.", ev=["anticipation_plaisir"]),
    ])
    j.seg("13:15", "Sieste", "sejour", "rt-repos", "sieste", "sommeil", "assis", [
        p("Pose le journal sur la table basse, ses lunettes sur le front, et ferme les yeux dans son fauteuil.", None, mode="eveille", charge="repos",
          objets=mvs([("obj-progres-0308", "sejour / dans sa main", "sejour / table basse"), ("obj-lunettes", "sur son nez", "sur son front")]))] +
        [p("Somnole dans le fauteuil.") for _ in range(10)] + [
        p("Se réveille, s'étire. Regarde par la porte-fenêtre le potager qui l'attend.", "Bon. Les radis.", mode="eveille", charge="repos",
          posture="debout")])

    # ------------------------------------------------------------ jardin
    j.seg("14:15", "Potager", "jardin", "rt-lundi", "effort", "simple", "debout", [
        p("Va chercher au garage la bêche, la griffe et les sachets de graines de radis, sort par la porte-fenêtre.", None, via=["garage"],
          objets=mvs([("obj-outils-jardin", "garage / outils de jardin", "jardin / potager")]), mode="eveille"),
        p("Retourne la terre du premier rang à la bêche.", None, ev=["effort_physique", "jardinage"]),
        p("Retourne la terre, motte après motte, en sifflotant « La Bohème ».", "Ça, c'est du travail qu'on voit."),
        p("Continue le premier rang.", None),
        p("S'arrête, une main dans le dos, et regarde le ciel.", "Le dos. Josiane avait raison, ce matin.", ev=["mal_de_dos"]),
        p("Reprend avec le deuxième rang, plus lentement.", None),
        p("Retourne la terre du deuxième rang.", None, ev=["effort_physique"]),
        p("Casse les mottes à la griffe.", None),
        p("Passe aux toilettes du rez-de-chaussée et boit un grand verre d'eau à la cuisine.", None, piece="cuisine", via=["wc"],
          effets={"toilettes": "vide", "soif": 25}, mode="eveille"),
        p("Ressort au potager et ratisse la terre fine.", None),
        p("Ratisse, enlève les cailloux.", None),
        p("Trace deux sillons au cordeau.", None, mode="eveille"),
        p("Sème les radis, en pinçant les graines entre deux doigts.", "Ma mère semait comme ça. Une pincée, un pas.", ev=["jardinage"], mode="eveille"),
        p("Sème le deuxième sillon.", None, mode="eveille"),
        p("Referme les sillons du plat de la main et tasse.", None, mode="eveille"),
        p("Arrose les semis à l'arrosoir.", None),
        p("Gérard Morel, le voisin d'en face, s'accoude à la haie : « Alors, Robert, tu plantes ou tu prends racine ? » Ils parlent de la belote "
          "de samedi.", "Gérard. Toujours une blague d'avance.", mode="eveille", ev=["bavardage_voisin", "rire"], effets={"social": 3}),
        p("Arrache les mauvaises herbes autour des fraisiers.", None),
        p("Continue le désherbage, à genoux sur un sac.", None),
        p("Coupe les tiges sèches des groseilliers.", None),
        p("Ramasse les feuilles et les mauvaises herbes dans la brouette.", None),
        p("Vide la brouette au compost, au fond du jardin.", None, ev=["effort_physique"]),
        p("S'assoit sur le muret et regarde le potager retourné.", "Dans trois semaines, les premiers radis. Lucas aime les croquer avec du sel.",
          ev=["pensee_claire"], mode="eveille", posture="assis"),
        p("Nettoie la bêche et la griffe au robinet du jardin.", None, mode="eveille"),
        p("Rentre la brouette.", None, mode="eveille"),
        p("Fait le tour du jardin : la haie, le cerisier, le banc.", None, mode="eveille", posture="en marche"),
        p("Rapporte les outils au garage.", "Bonne journée de terre.", piece="garage", mode="eveille", ev=["repos_merite"],
          objets=mvs([("obj-outils-jardin", "jardin / potager", "garage / outils de jardin")])),
    ])
    j.seg("16:30", "Garage", "garage", "rt-lundi", "eveille", "simple", "debout", [
        p("Range les outils de jardin au mur, chacun à son crochet.", None),
        p("Graisse les gonds de la porte basculante, qui grince depuis l'hiver.", None, charge="precision"),
        p("Ouvre et ferme la porte basculante pour vérifier.", "Plus un bruit. Voilà."),
        p("Boit un verre d'eau au robinet de l'évier du garage, puis vérifie la pression des pneus de la Kangoo au gonfleur.", None,
          charge="precision", effets={"soif": 20}),
        p("Regonfle le pneu arrière gauche.", None),
        p("Range l'établi, trie les vis dans les pots de confiture.", None),
        p("Recolle le pied de la chaise de la cuisine, que Josiane réclame depuis Noël.", None, charge="precision"),
        p("Serre le serre-joint et laisse sécher.", "Demain elle s'assoit dessus. Faudra pas qu'elle bouge.", charge="precision"),
        p("Balaie le garage.", None),
        p("Compte les bouteilles de vin à côté du congélateur : trois.", None),
        p("Passe aux toilettes du rez-de-chaussée.", None, piece="wc", effets={"toilettes": "vide"}),
        p("Se lave les mains à la cuisine.", None, piece="cuisine", effets={"hygiene": 10}),
    ])

    # ------------------------------------------------------------ fin d'après-midi
    j.seg("17:30", "Café, radio et mots croisés", "sejour", "rt-repos", "lecture", "lecture", "assis", [
        p("Se fait un café, allume la radio de la cuisine, porte ouverte, et s'installe au séjour avec son recueil de mots croisés.", None, via=["cuisine"],
          app=onoff(["radio-cuisine", "cafetiere-maison"], ["cafetiere-maison"]), radio=True, effets={"cafe": True, "soif": 10},
          consommation=[c("cafe_moulu", 7)], objets=mvs([("obj-lunettes", "sur son front", "sur son nez")]), ev=["plaisir_simple"]),
        p("Cherche « épicier en gros », neuf lettres.", "Grossiste. Évidemment.", radio=True, ev=["rire"]),
        p("Fait sa grille, la radio en fond.", None, radio=True),
        p("Josiane lui apporte un verre de sirop de grenadine ; ils parlent de la sœur de Josiane.", None,
          radio=True, effets={"social": 1.0, "soif": 20}),
        p("Cherche un mot de sept lettres pour « qui ne change pas ».", "Routinier. Josiane dirait que c'est moi.", radio=True),
        p("Écoute les informations de dix-huit heures : la neige dans le Roussillon, des milliers de foyers sans électricité.", None, radio=True),
        p("Regarde la photo de Claire et des petits sur le buffet.", "Noël. Emma avait peur du Père Noël de la galerie.", radio=True,
          ev=["pensee_claire"]),
        p("Pense au cadeau de Josiane.", "Un bijou ? Elle en porte jamais. Un week-end à Sète ? C'est pour l'an prochain, ça.", radio=True,
          ev=["anniversaire_mariage"]),
        p("Passe aux toilettes du rez-de-chaussée.", None, piece="wc", posture="debout", mode="eveille", charge="simple", effets={"toilettes": "vide"}),
        p("Revient à sa grille. La nuit tombe ; il allume la lampe du séjour.", None, radio=True, app=on("lumiere-sejour")),
        p("Termine la grille, sauf deux cases.", None, radio=True),
        p("Josiane l'appelle : « On mange tôt, si on veut être à l'heure. »", None, radio=True, effets={"social": 1.0}),
        p("Pose le recueil sur la table basse et remonte ses lunettes.", None, radio=True,
          objets=mvs([("obj-lunettes", "sur son nez", "sur son front")])),
        p("Met la table dans la cuisine.", None, piece="cuisine", posture="debout", mode="eveille", charge="simple", radio=True),
        p("Remplit la carafe d'eau, coupe le pain.", None, piece="cuisine", posture="debout", mode="eveille", charge="simple", radio=True),
    ])
    j.seg("18:45", "Dîner tôt avec Josiane", "cuisine", "rt-repas", "eveille", "repos", "assis", [
        p("Éteint la radio. Soupe de légumes avec Josiane, face à face à la table de la cuisine ; un grand verre d'eau d'abord.", None,
          app=off("radio-cuisine"), ev=["moment_josiane"], effets={"social": 1.0, "soif": 20}),
        p("Mange la soupe de carottes avec un quart de baguette.", "Pas de vin ce soir. Je conduis.", effets={"faim": 35, "social": 1.0},
          consommation=ingredients(fiche, "lundi", "diner")),
        p("Le comté, en dessert.", None, effets={"faim": 15, "social": 1.0}),
        p("Josiane lui demande comment va la caisse. Il dit que ça va.", "Ça va pas. Mais elle a assez de son dos.", effets={"social": 1.0}),
        p("Josiane lui raconte le début du film d'après Le Progrès : un écrivain, une île, un ancien ministre anglais.", None, effets={"social": 1.0}),
        p("Débarrasse la table.", None, posture="debout", charge="simple"),
        p("Essuie la vaisselle pendant que Josiane lave.", None, posture="debout", charge="simple", effets={"social": 1.0}),
        p("Boit un verre d'eau.", None, posture="debout", charge="simple", effets={"soif": 20}),
        p("Éteint le séjour et monte se changer.", None, posture="debout", charge="simple", app=off("lumiere-sejour")),
    ])

    # ------------------------------------------------------------ cinéma
    j.seg("19:30", "Se prépare pour sortir", "chambre", "rt-lundi", "eveille", "simple", "debout", [
        p("Passe une chemise propre et le pantalon gris du dimanche.", None, effets={"hygiene": 5}),
        p("Se recoiffe dans la salle de bain, passe aux toilettes.", None, piece="salle-de-bain", effets={"toilettes": "vide"}),
        p("Attend Josiane au pied de l'escalier en regardant sa montre.", "Vingt heures quinze, elle a dit. On sera juste.", piece="entree"),
        p("Josiane descend, manteau sur le dos. Il prend sa veste, ses clés, celles de la Kangoo et son portefeuille, ouvre le garage.", None,
          piece="garage", ev=["sortie_couple"], effets={"social": 1.0},
          objets=mvs([("obj-veste", "entree / portemanteau", "porté"), ("obj-cles", "entree / vide-poche", "poche de la veste"),
                      ("obj-cles-kangoo", "entree / vide-poche", "dans sa main"), ("obj-portefeuille", "entree / vide-poche", "poche de la veste")])),
    ])
    j.seg("19:50", "Route vers la Cité internationale", KANGOO, "rt-lundi", "eveille", "conduite", "assis", en_voiture([
        "Sort la Kangoo, éteint le garage, Josiane à côté de lui. Rue des Glycines, puis le cours Émile-Zola, dégagé à cette heure.",
        "Boulevard de Stalingrad le long du parc de la Tête d'Or, illuminé.",
        "Descend au parking souterrain de la Cité internationale et se gare au deuxième sous-sol.",
    ], [(1500, 0), (1300, 0), (700, 0)], pensees=["Josiane a mis son parfum. Ça faisait longtemps.", None, None],
        ev=[["sortie_couple"], None, None],
        extra={0: {"objets": mvs([("obj-kangoo", "garage / place de la Kangoo", "en route"), ("obj-cles-kangoo", "dans sa main", "contact de la Kangoo")]),
                   "app": off("lumiere-garage"), "effets": {"social": 1.0}},
               2: {"objets": mvs([("obj-kangoo", "en route", "parking de la Cité internationale / deuxième sous-sol"),
                                  ("obj-cles-kangoo", "contact de la Kangoo", "poche de la veste")])}}), lieu=TRAJET)
    j.seg("20:05", "Billets", "UGC Ciné Cité Internationale", "rt-lundi", "eveille", "simple", "en marche", [
        p("Remonte du parking avec Josiane, longe le Rhône jusqu'au cinéma. Prend deux places pour « The Ghost Writer », séance de 20 h 15, "
          "et paie par carte.", "Dix-huit euros soixante. Le cinéma, c'est devenu un luxe.", parcours=[marche(250)], lieu="cinema-ugc",
          argent={"compte": -18.6}, effets={"social": 1.0},
          nouveaux_objets=[{"id": "obj-billets-cinema", "nom": "Deux billets de cinéma (« The Ghost Writer », lundi 8 mars, 20 h 15)",
                            "position": "poche de la veste"}]),
        p("Entre dans la salle 6, s'installe avec Josiane au milieu du rang, retire sa veste.", None, posture="assis", lieu="cinema-ugc",
          effets={"social": 1.0}),
    ])
    # Séance de 20:15 : bandes-annonces jusqu'à 20:30, film de 2 h 08 jusqu'à 22:38, générique.
    temps_forts = {
        0: ("Les bandes-annonces, le son très fort.", None, []),
        1: ("Les bandes-annonces. Josiane lui glisse : « Celui-là, on ira. »", None, []),
        2: ("Les dernières publicités ; la salle s'éteint.", None, []),
        3: ("Le film commence : un écrivain anglais accepte de finir les mémoires d'un ancien Premier ministre britannique.", None, []),
        5: ("Le ferry, la pluie, une maison de verre sur une île américaine.", "Il pleut tout le temps, chez eux.", []),
        7: ("Le nègre littéraire apprend que son prédécesseur s'est noyé.", "Ça sent pas bon, cette histoire.", ["film_prenant"]),
        10: ("S'assoupit un instant ; Josiane lui donne un coup de coude.", None, []),
        11: ("Se redresse, se frotte les yeux, reprend le fil.", "J'ai raté quoi ? L'ancien ministre est accusé de quelque chose.", []),
        14: ("Suit le film, penché en avant.", None, ["film_prenant"]),
        16: ("Une course à vélo sous la pluie, un vieux GPS qui se souvient du dernier trajet.", None, ["film_prenant"]),
        19: ("Josiane serre son bras.", None, ["film_prenant"]),
        21: ("La tension monte ; il ne bouge plus.", "Il est fort, ce Polanski. Je l'aurais pas cru.", ["film_prenant"]),
        24: ("Les révélations s'enchaînent, dans une salle de réception.", None, ["film_prenant"]),
        27: ("La fin du film, dans une rue de Londres, sans un bruit.", "Ah. Bon. Ben dis donc.", ["film_prenant"]),
        28: ("Le générique. Ils restent assis le temps que la salle se vide ; Josiane parle déjà de la fin.", None, ["sortie_couple"]),
    }
    seance = [p(*temps_forts.get(k, ("Suit le film.", None, []))[:2], ev=temps_forts.get(k, (0, 0, []))[2],
                effets={"social": 0.5}) for k in range(29)]
    j.seg("20:15", "Cinéma avec Josiane", "UGC Ciné Cité Internationale", "rt-lundi", "loisir", "lecture", "assis", seance, lieu="cinema-ugc")
    j.seg("22:40", "Retour du cinéma", "parking de la Cité internationale", "rt-lundi", "eveille", "simple", "en marche", [
        p("Ressort avec Josiane, longe le Rhône jusqu'au parking. Ils ne sont pas d'accord sur la fin.", "Elle a compris avant moi. Comme toujours.",
          parcours=[marche(250)], lieu="exterieur", effets={"social": 1.0}, ev=["rire"]),
    ])
    j.seg("22:45", "Retour en Kangoo", KANGOO, "rt-lundi", "eveille", "conduite", "assis", en_voiture([
        "Remonte du parking, boulevard de Stalingrad.",
        "Cours Émile-Zola, presque désert.",
        "Rue des Glycines ; rentre la Kangoo au garage.",
    ], [(700, 0), (1300, 0), (1500, 0)], ev=[["conduite_tranquille"], None, None],
        extra={0: {"objets": mvs([("obj-kangoo", "parking de la Cité internationale / deuxième sous-sol", "en route"),
                                  ("obj-cles-kangoo", "poche de la veste", "contact de la Kangoo")])}}), lieu=TRAJET)

    # ------------------------------------------------------------ coucher
    j.seg("23:00", "Toilette du soir", "entree", "rt-soir", "eveille", "simple", "debout", [
        p("Entre par le garage, accroche sa veste, pose les clés, le portefeuille et les billets dans le vide-poche.", None, retour="garage",
          objets=mvs([("obj-kangoo", "en route", "garage / place de la Kangoo"), ("obj-cles-kangoo", "contact de la Kangoo", "entree / vide-poche"),
                      ("obj-cles", "poche de la veste", "entree / vide-poche"), ("obj-portefeuille", "poche de la veste", "entree / vide-poche"),
                      ("obj-billets-cinema", "poche de la veste", "entree / vide-poche"), ("obj-veste", "porté", "entree / portemanteau")])),
        p("Monte à l'étage. Passe aux toilettes, se brosse les dents, boit un verre d'eau au lavabo.", None, piece="salle-de-bain",
          effets={"toilettes": "vide", "hygiene": 10, "soif": 15}),
        p("Enfile son pyjama rayé.", None, piece="salle-de-bain"),
        p("Pose sa Seiko et ses lunettes sur sa table de chevet et se couche à côté de Josiane.", "Cinq heures et demie. Ça va piquer.",
          piece="chambre", posture="allongé", charge="repos",
          objets=mvs([("obj-montre", "poignet gauche", "chambre / table de chevet de Robert"),
                      ("obj-lunettes", "sur son front", "chambre / table de chevet de Robert")])),
    ])
    j.seg("23:20", "Endormissement", "chambre", "rt-soir", "eveille", "repos", "allongé", [
        p("Éteint la lampe de chevet.", None, app=off("lumiere-chambre")),
        p("Repense au film, à la maison de verre sous la pluie.", None),
        p("S'endort.", None, charge="sommeil"),
    ])
    j.seg("23:35", "Sommeil", "chambre", "sommeil", "sommeil", "sommeil", "allongé", nuit([
        ("23:35", "24:00", "léger", None, None),
    ]))
    j.extinction = "23:20"
    j.ecarts = ["Dîner avancé à 18:45 et coucher à 23:20 : soirée au cinéma avec Josiane (« The Ghost Writer »)."]
    j.bilan = [f"**Recette de la semaine passée déposée au coffre de la banque** : {euros(etat['argent']['coffre'])}.",
               "**Boutique** : grand ménage, deux packs de yaourts et une laitue jetés.",
               f"**Bon de commande** : {len(commande)} lignes pour la livraison de mardi.",
               "**Pour la maison** : un sac de pommes de terre, des carottes et une laitue prélevés au magasin.",
               "**Potager** : deux rangs retournés, radis semés.",
               "**Cinéma** avec Josiane : « The Ghost Writer » de Roman Polanski, à l'UGC Ciné Cité Internationale."]
    j.commande = commande
    return j
