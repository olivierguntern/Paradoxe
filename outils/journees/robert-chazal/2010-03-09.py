"""Mardi 9 mars 2010 — contenu rédigé de la journée de Robert Chazal.

Nuit courte après le cinéma. Réveil à 5 h 30, Kangoo, pain et Progrès à
6 h 35, livraison du grossiste à 6 h 40, ouverture à 7 h. Mme Ferrand et
M. Benali le matin ; déjeuner à la maison avec Josiane et sieste ; l'après-
midi, M. Garnier sur le pas de la porte, les Grosses Têtes à la radio, les
étudiantes du 7 et l'horloger, qui achète trois pommes et trois bananes.
Le soir, il rapporte de quoi faire l'omelette et le poulet basquaise.
"""
import json
import os

from commun import (ALLER, ARRIVEE_BOUTIQUE, ARRIVEE_MAISON, BOUTIQUE, DEPART_BOUTIQUE, KANGOO, RETOUR, RETOUR_LENT, TRAJET, Magasin,
                    en_voiture, euros, ingredients, mvs, nuit)
from moteur import Journee, c, off, on, onoff, p

FICHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "personnages", "robert-chazal.json")


def rediger(etat):
    fiche = json.load(open(FICHE))
    j = Journee("2010-03-09", "mardi", extinction="22:00")
    mag = Magasin(fiche, etat, "2010-03-09", "mardi")
    commande = mag.commande()  # le bon écrit lundi : rien n'a bougé depuis
    nb_lignes = len(commande)

    # ------------------------------------------------------------ nuit
    # Endormi à 23:35 après le cinéma.
    j.seg("00:00", "Nuit de lundi à mardi", "chambre", "sommeil", "sommeil", "sommeil", "allongé", nuit([
        ("00:00", "00:40", "profond", None, None),
        ("00:40", "00:55", "léger", None, None),
        ("00:55", "01:05", "paradoxal", None, None),
        ("01:05", "01:20", "léger", None, None),
        ("01:20", "02:00", "profond", None, None),
        ("02:00", "02:15", "léger", None, None),
        ("02:15", "02:35", "paradoxal", "Une maison de verre au bord de la mer ; il y cherche sa caisse enregistreuse et ne trouve que des manuscrits.", "reve_inquiet"),
        ("02:35", "02:50", "léger", None, None),
        ("02:50", "03:20", "profond", None, None),
        ("03:20", "03:40", "léger", None, None),
        ("03:40", "04:05", "paradoxal", "Le Bernabéu est plein ; il vend des baguettes dans les tribunes et tout le monde paie en pesetas.", None),
        ("04:05", "04:10", "micro-éveil", None, None),
        ("04:10", "04:35", "léger", None, None),
        ("04:35", "04:50", "profond", None, None),
        ("04:50", "05:30", "léger", None, None),
    ]))

    # ------------------------------------------------------------ matin
    j.seg("05:30", "Réveil", "chambre", "rt-commerce", "eveille", "repos", "assis", [
        p("Le réveil sonne, réglé bas. Il l'arrête avant la deuxième sonnerie, s'assoit au bord du lit dans le noir, attache sa Seiko, "
          "prend ses lunettes.", "Six heures de sommeil. Polanski, va.", ev=["reveil_sonnerie"],
          objets=mvs([("obj-montre", "chambre / table de chevet de Robert", "poignet gauche"),
                      ("obj-lunettes", "chambre / table de chevet de Robert", "sur son front")])),
    ])
    j.seg("05:35", "Toilette", "salle-de-bain", "rt-commerce", "eveille", "simple", "debout", [
        p("Passe aux toilettes de la salle de bain, sans tirer la chasse trop fort.", None, effets={"toilettes": "vide"}),
        p("Douche rapide, l'eau bien chaude sur les reins.", None, effets={"hygiene": 75}, ev=["plaisir_simple"]),
        p("Se rase.", None, charge="precision"),
        p("S'habille dans la salle de bain avec les vêtements posés la veille sur le tabouret.", None),
    ])
    j.seg("05:55", "Petit-déjeuner", "cuisine", "rt-commerce", "eveille", "cuisine", "debout", [
        p("Descend à la cuisine sans allumer l'escalier trop longtemps. Met la cafetière en route et la radio tout bas, beurre deux tartines.", None,
          app=on("cafetiere-maison", "radio-cuisine"), radio=True),
        p("Mange debout contre le buffet, le café sucré, les tartines à la confiture d'abricots ; avale son comprimé avec un verre d'eau.",
          "Les informations parlent encore de la neige à Perpignan.", charge="repos", radio=True,
          effets={"faim": 40, "soif": 30, "cafe": True}, consommation=ingredients(fiche, None, "petit_dejeuner"), ev=["plaisir_simple"]),
        p("Rince son bol, laisse le reste du café au chaud dans le thermos pour Josiane, éteint la radio et la cafetière.", None,
          app=off("cafetiere-maison", "radio-cuisine")),
    ])
    j.seg("06:10", "Départ", "garage", "rt-commerce", "eveille", "simple", "debout", [
        p("Prend sa veste, ses clés, celles de la Kangoo, son portefeuille et le cabas vide au portemanteau. Ouvre la porte basculante.", None,
          objets=mvs([("obj-veste", "entree / portemanteau", "porté"), ("obj-cles", "entree / vide-poche", "poche de la veste"),
                      ("obj-cles-kangoo", "entree / vide-poche", "dans sa main"), ("obj-portefeuille", "entree / vide-poche", "poche de la veste"),
                      ("obj-cabas-boutique", "entree / portemanteau", "dans sa main")])),
    ])
    j.seg("06:15", "Route vers la Croix-Rousse", KANGOO, "rt-commerce", "eveille", "conduite", "assis", en_voiture([
        "Sort la Kangoo, éteint le garage, referme. Rue des Glycines, cours Émile-Zola désert, les feux à l'orange clignotant.",
        "Boulevard de Stalingrad, pont Winston-Churchill. Le Rhône est noir, les quais encore éclairés.",
        "Monte la montée de la Boucle, longe le boulevard et entre dans la cour de l'épicerie.",
    ], ALLER, pensees=["RTL Matin. Ils parlent des régionales.", None, "Le grossiste à six heures quarante. Pile."],
        ev=[["conduite_tranquille"], None, None],
        extra={0: {"objets": mvs([("obj-kangoo", "garage / place de la Kangoo", "en route"), ("obj-cles-kangoo", "dans sa main", "contact de la Kangoo")]),
                   "app": off("lumiere-garage")}}), lieu=TRAJET)

    # ------------------------------------------------------------ boutique : arrivée et livraisons
    pain = {"baguette": 70, "pain_campagne": 6}
    invendus = {k: mag.stock[k] for k in pain}
    j.seg("06:30", "Arrivée à la boutique", "arriere-boutique", "rt-commerce", "eveille", "simple", "debout", [
        p("Gare la Kangoo dans la cour, entre par la porte de derrière. Accroche sa veste et le cabas à la patère, enfile sa blouse.", None,
          retour="cour-epicerie",
          objets=mvs(ARRIVEE_BOUTIQUE + [("obj-cabas-boutique", "dans sa main", "arriere-boutique / patère")])),
    ], lieu=BOUTIQUE)
    j.seg("06:35", "Livraison du pain", "boutique", "rt-commerce", "eveille", "simple", "debout", [
        p("Allume la boutique, lève le rideau à mi-hauteur. Le livreur de la boulangerie de la place pose deux panières : soixante-dix baguettes, "
          "six pains de campagne, et Le Progrès sur le dessus. Robert met de côté une baguette pour la maison.", "Il a encore oublié de me compter "
          "le journal de la semaine dernière. Je lui dirai vendredi.", via=["trottoir"], app=on("lumiere-boutique"),
          livraisons=mag.livrer(pain), reprises=mag.reprendre(invendus, "invendus de la veille repris par le livreur"),
          prelevements=[mag.pour_maison("pain", 1)],
          nouveaux_objets=[{"id": "obj-progres-0309", "nom": "Le Progrès du mardi 9 mars 2010", "position": "boutique / comptoir"}]),
    ], lieu=BOUTIQUE)
    j.seg("06:40", "Livraison du grossiste", "reserve", "rt-commerce", "effort", "simple", "debout", [
        p("Le camion du grossiste entre dans la cour en marche arrière. Robert tend le bon de commande au chauffeur, qui décharge sur le diable.",
          "Trente et une lignes. Le chauffeur dit que le lait augmente en avril.", via=["cour-epicerie"], ev=["livraison"], livraisons=mag.livrer(commande),
          mode="travail"),
        p("Rentre les cagettes de pommes, d'oranges et de bananes, puis les packs de lait et d'eau.", None, ev=["effort_physique"]),
        p("Porte les cartons d'épicerie sur les étagères de la réserve, signe le bon de livraison, remplit l'étal de pommes et d'oranges, "
          "puis se tient les reins une minute.", "Le dos. Quatre ans encore. Quatre ans.", piece="boutique", ev=["effort_physique", "mal_de_dos"]),
    ], lieu=BOUTIQUE)
    j.seg("06:55", "Ouverture", "boutique", "rt-commerce", "eveille", "simple", "debout", [
        p("Lève le rideau de fer en entier, allume la radio de la boutique et la caisse enregistreuse, compte le fond de caisse : cent cinquante euros.",
          None, via=["trottoir"], app=on("radio-boutique", "caisse"), radio=True),
    ], lieu=BOUTIQUE)

    # ------------------------------------------------------------ matinée
    vide_matin = [
        "Range les packs de lait dans la vitrine réfrigérée.",
        "Aligne les boîtes de conserve, les étiquettes vers la rue.",
        "Essuie le comptoir.",
        "Regarde passer les premiers bus dans la Grande-Rue.",
        "Met en rayon les paquets de café arrivés ce matin.",
        "Redresse les cagettes de l'étal.",
        "Range les sachets de bonbons dans les bocaux, pour les gamins de l'école.",
        "Fait la monnaie dans le tiroir de la caisse.",
        "Chantonne avec la radio.",
        "Vérifie les dates des yaourts livrés.",
    ]
    notes_matin = {
        "07:05": {"action": "Entre deux clients, va chercher un carton de lait à la réserve.", "via": ["reserve"]},
        "07:20": {"action": "Ouvre les cartons de conserves et remplit les rayons du fond.", "via": ["reserve"]},
        "07:45": {"pensee": "Les gens du chantier de la place prennent leur sandwich à la supérette, maintenant."},
        "07:50": {"action": "Déplie Le Progrès sur le comptoir.", "ev": ["lecture_journal"], "pensee": "Page des sports : tout le journal parle de Madrid."},
        "08:15": {"pensee": "Quatre-vingt-deux ans, et elle sait tout ce qui se passe dans la rue avant tout le monde."},
        "09:00": {"pensee": "Josiane doit être au cabinet. Le docteur en retard, comme d'habitude."},
        "09:30": {"action": "Passe aux toilettes du fond, se fait un café dans l'arrière-boutique et revient au comptoir avec la tasse de Lucas.",
                  "via": ["wc-boutique", "arriere-boutique"], "effets": {"toilettes": "vide", "cafe": True, "soif": 15},
                  "consommation": [c("cafe_boutique", 7)], "app": onoff(["cafetiere-boutique"], ["cafetiere-boutique"]), "ev": ["plaisir_simple"],
                  "objets": mvs([("obj-tasse-boutique", "arriere-boutique / évier", "boutique / comptoir")])},
        "10:00": {"pensee": "Le 16. Trente-quatre ans. Un bijou, non. Un restaurant, peut-être. À Sète, l'an prochain.", "ev": ["anniversaire_mariage"]},
        "10:15": {"action": "Lit Le Progrès entre deux clients : les élections régionales, la neige dans le Roussillon.", "ev": ["lecture_journal"]},
        "10:40": {"pensee": "Ahmed. Trente ans qu'il critique le pain des autres."},
        "11:00": {"action": "Boit un grand verre d'eau à l'évier de l'arrière-boutique.", "via": ["arriere-boutique"], "effets": {"soif": 25}},
        "11:30": {"pensee": "La matinée est correcte. Le midi, ça repart toujours un peu."},
        "11:50": {"action": "Commence à resserrer l'étal de fruits avant midi."},
    }
    j.seg("07:00", "Boutique ouverte", "boutique", "rt-commerce", "travail", "service", "debout",
          mag.service("07:00", "12:00", "Boutique ouverte", "rt-commerce", vide_matin, notes_matin), lieu=BOUTIQUE)

    # ------------------------------------------------------------ midi
    recette_matin = mag.recette()
    argent_midi, especes_midi = mag.vider_caisse()
    j.seg("12:00", "Fermeture de midi", "boutique", "rt-commerce", "eveille", "simple", "debout", [
        p("Baisse le rideau de fer, éteint la radio et la caisse.", None, via=["trottoir"], app=off("radio-boutique", "caisse")),
        p(f"Dans l'arrière-boutique, compte la caisse du matin : {euros(especes_midi)} en espèces au-delà du fond, qu'il range dans la sacoche du coffre. "
          "Rince la tasse de Lucas.", f"{euros(recette_matin)} ce matin, cartes comprises. Ça va.", piece="arriere-boutique", charge="precision",
          argent=argent_midi, app=off("lumiere-boutique"), objets=mvs([("obj-tasse-boutique", "boutique / comptoir", "arriere-boutique / évier")])),
    ], lieu=BOUTIQUE)
    j.seg("12:10", "Retour déjeuner", KANGOO, "rt-commerce", "eveille", "conduite", "assis", en_voiture([
        "Raccroche sa blouse, remet sa veste, sort par la cour et démarre. Descend la montée de la Boucle.",
        "Pont Winston-Churchill, boulevard de Stalingrad.",
        "Cours Émile-Zola, rue des Glycines ; rentre la Kangoo au garage.",
    ], RETOUR, ev=[None, ["conduite_tranquille"], None],
        extra={0: {"sortie": "cour-epicerie", "objets": mvs(DEPART_BOUTIQUE)}}), lieu=TRAJET)
    j.seg("12:25", "Déjeuner avec Josiane", "cuisine", "rt-repas", "eveille", "repos", "assis", [
        p("Entre par le garage, accroche sa veste, pose ses clés et son portefeuille. Josiane réchauffe le reste de gratin et lave la laitue.", None,
          retour="garage", posture="debout", objets=mvs(ARRIVEE_MAISON), effets={"social": 1.0}),
        p("Se lave les mains, boit un verre d'eau, s'assoit.", None, effets={"soif": 20, "hygiene": 10}),
        p("Mangent le reste de gratin et la salade verte.", "Le gratin, il est meilleur réchauffé.", ev=["moment_josiane", "plaisir_simple"],
          effets={"faim": 50, "social": 1.0}, consommation=ingredients(fiche, "mardi", "dejeuner")),
        p("Josiane demande si le film lui a plu. Il avoue qu'il a dormi un peu. Elle rit.", None, effets={"social": 1.0}, ev=["rire"]),
        p("Josiane : « Ce soir, une omelette. Rapporte des œufs, il en reste deux. Et des tomates pour demain. »",
          "Des œufs, des tomates. Des œufs, des tomates.", effets={"social": 1.0}),
        p("Mange une pomme.", None, effets={"social": 1.0, "faim": 5}),
        p("Se fait un café à la cafetière électrique et le boit debout.", None, posture="debout", charge="cuisine",
          effets={"cafe": True, "soif": 10}, app=onoff(["cafetiere-maison"], ["cafetiere-maison"]), consommation=[c("cafe_moulu", 7)]),
        p("Passe aux toilettes du rez-de-chaussée.", None, piece="wc", posture="debout", charge="simple", effets={"toilettes": "vide"}),
        p("Embrasse Josiane, s'installe dans son fauteuil.", None, piece="sejour", charge="repos"),
    ])
    j.seg("13:10", "Sieste", "sejour", "rt-repos", "sieste", "sommeil", "assis", [
        p("S'endort aussitôt dans le fauteuil, les lunettes sur le front."),
        p("Somnole."),
        p("Somnole ; Josiane ferme les volets à moitié."),
    ])
    j.seg("13:25", "Départ", "garage", "rt-commerce", "eveille", "simple", "debout", [
        p("Se réveille d'un coup, regarde sa montre. Prend sa veste, ses clés et son portefeuille, ouvre le garage.", "Déjà. Allez.",
          objets=mvs([("obj-veste", "entree / portemanteau", "porté"), ("obj-cles", "entree / vide-poche", "poche de la veste"),
                      ("obj-cles-kangoo", "entree / vide-poche", "dans sa main"), ("obj-portefeuille", "entree / vide-poche", "poche de la veste")])),
    ])
    j.seg("13:30", "Retour à la boutique", KANGOO, "rt-commerce", "eveille", "conduite", "assis", en_voiture([
        "Sort la Kangoo, éteint le garage. Cours Émile-Zola.",
        "Pont Winston-Churchill ; le soleil sur le Rhône.",
        "Montée de la Boucle, boulevard, cour de l'épicerie.",
    ], ALLER, ev=[None, ["conduite_tranquille"], None],
        extra={0: {"objets": mvs([("obj-kangoo", "garage / place de la Kangoo", "en route"), ("obj-cles-kangoo", "dans sa main", "contact de la Kangoo")]),
                   "app": off("lumiere-garage")}}), lieu=TRAJET)
    j.seg("13:45", "Réouverture", "arriere-boutique", "rt-commerce", "eveille", "simple", "debout", [
        p("Entre par la cour, accroche sa veste, enfile sa blouse.", None, retour="cour-epicerie", objets=mvs(ARRIVEE_BOUTIQUE)),
        p("Allume la boutique, remplit l'étal de bananes depuis la réserve.", None, piece="boutique", via=["reserve"], app=on("lumiere-boutique")),
        p("Lève le rideau, rallume la radio et la caisse.", None, piece="boutique", via=["trottoir"], app=on("radio-boutique", "caisse"), radio=True),
    ], lieu=BOUTIQUE)

    # ------------------------------------------------------------ après-midi
    vide_apres = [
        "Écrit à la main une étiquette « Oranges de Valence ».",
        "Range la réserve après la livraison du matin.",
        "Aplatit les cartons vides.",
        "Regarde la Grande-Rue par la vitrine ; deux mères avec des poussettes remontent vers la place.",
        "Recopie les ventes du matin dans le cahier.",
        "Redresse les boîtes de conserve.",
        "Remet de l'ordre dans le présentoir de cartes postales.",
        "Essuie la vitrine réfrigérée.",
        "Chantonne avec la radio.",
        "Compte les sacs de pommes de terre de la réserve.",
    ]
    notes_apres = {
        "14:00": {"pensee": "L'après-midi, c'est calme jusqu'à quatre heures. Toujours."},
        "14:20": {"action": "Relit Le Progrès, la page de l'OL, accoudé au comptoir.", "ev": ["lecture_journal"],
                  "pensee": "Madrid, c'est pas Gerland. Faudra tenir."},
        "14:45": {"action": "Boit un verre d'eau à l'arrière-boutique.", "via": ["arriere-boutique"], "effets": {"soif": 25}},
        "15:10": {"action": "M. Garnier, le buraliste, sort fumer sur le trottoir ; Robert le rejoint sur le pas de la porte. Ils parlent du match "
                            "de demain et de la supérette.", "via": ["trottoir"], "ev": ["bavardage_voisin"], "effets": {"social": 2},
                  "pensee": "Garnier dit que la supérette va fermer le dimanche. On verra."},
        "15:40": {"pensee": "Claire. Ça fait trois semaines qu'on les a pas vus. Pâques, c'est loin.", "ev": ["pensee_claire"]},
        "16:00": {"action": "À la radio, les Grosses Têtes commencent ; il monte un peu le son.", "ev": ["plaisir_simple"]},
        "16:30": {"action": "Se fait un café dans l'arrière-boutique et le boit au comptoir.", "via": ["arriere-boutique"],
                  "effets": {"cafe": True, "soif": 15}, "consommation": [c("cafe_boutique", 7)],
                  "app": onoff(["cafetiere-boutique"], ["cafetiere-boutique"]),
                  "objets": mvs([("obj-tasse-boutique", "arriere-boutique / évier", "boutique / comptoir")])},
        "16:45": {"action": "Éclate de rire à une blague de Bouvard à la radio.", "ev": ["rire"]},
        "17:00": {"action": "Remplit l'étal de pommes depuis la réserve.", "via": ["reserve"]},
        "17:20": {"action": "Passe aux toilettes du fond pendant un creux.", "via": ["wc-boutique"], "effets": {"toilettes": "vide"}},
        "17:40": {"action": "Boit un verre d'eau.", "via": ["arriere-boutique"], "effets": {"soif": 20}},
        "18:05": {"pensee": "Des pâtes, des pâtes. À leur âge, je mangeais pareil."},
        "18:20": {"client": {"texte": "L'horloger de la rue d'Austerlitz pousse la porte. « Bonsoir. » Robert lève la tête de sa caisse : « Tiens, "
                                     "l'horloger ! Alors, ces montres, ça avance ? » — « Doucement, mais ça avance. » Il le laisse choisir dans les rayons.",
                             "ev": ["client_habitue"], "social": 3},
                  "pensee": "Toujours seul, ce garçon. Il parle à ses montres plus qu'aux gens."},
        "18:25": {"client": {"texte": "L'horloger pose sur le comptoir trois pommes et trois bananes. « Ça fera 2,10 €. » Il paie en espèces. "
                                     "« Bonne soirée, monsieur Chazal. » — « À jeudi ! »",
                             "ventes": [{"produit": "pommes", "quantite": 3, "paiement": "especes"},
                                        {"produit": "bananes", "quantite": 3, "paiement": "especes"}]},
                  "pensee": "Il a l'air fatigué. Les montres, ça use les yeux."},
        "18:50": {"action": "Commence à rentrer l'étal de fruits pour la nuit."},
    }
    j.seg("14:00", "Boutique ouverte", "boutique", "rt-commerce", "travail", "service", "debout",
          mag.service("14:00", "19:00", "Boutique ouverte", "rt-commerce", vide_apres, notes_apres), lieu=BOUTIQUE)

    # ------------------------------------------------------------ fermeture
    recette = mag.recette()
    argent_soir, especes_soir = mag.vider_caisse()
    cabas = [mag.pour_maison("oeufs", 1), mag.pour_maison("oignons", 1), mag.pour_maison("tomates", 1)]
    j.seg("19:00", "Fermeture", "boutique", "rt-commerce", "eveille", "simple", "debout", [
        p("Rentre l'étal, baisse le rideau de fer, ferme la porte vitrée à clé, éteint la radio et la caisse.", None, via=["trottoir"],
          app=off("radio-boutique", "caisse")),
        p(f"Compte la caisse au bureau : {euros(especes_soir)} en espèces depuis midi, qu'il range dans la sacoche du coffre. La caisse tombe juste. "
          f"La journée fait {euros(recette)}.", "Juste en dessous de trois cents. Comme d'habitude, maintenant." if recette < 300 else
          "Au-dessus de trois cents. Ça arrive encore.", piece="arriere-boutique", charge="precision", posture="assis", argent=argent_soir,
          ev=["caisse_juste"] + (["constat_chiffre"] if recette < 300 else []),
          objets=mvs([("obj-tasse-boutique", "boutique / comptoir", "arriere-boutique / évier")])),
        p("Remplit le cabas pour Josiane : une boîte d'œufs, un oignon, une barquette de tomates. Glisse Le Progrès dessus, éteint la boutique.",
          "Des œufs, des tomates. Voilà.", piece="arriere-boutique", prelevements=cabas, app=off("lumiere-boutique"),
          objets=mvs([("obj-cabas-boutique", "arriere-boutique / patère", "dans sa main"), ("obj-progres-0309", "boutique / comptoir", "dans le cabas")])),
    ], lieu=BOUTIQUE)
    j.seg("19:15", "Retour à la maison", KANGOO, "rt-commerce", "eveille", "conduite", "assis", en_voiture([
        "Raccroche sa blouse, remet sa veste, sort par la cour. Descend la montée de la Boucle dans la file des phares.",
        "Pont Winston-Churchill, au pas.",
        "Boulevard de Stalingrad, puis le cours Émile-Zola, de feu rouge en feu rouge.",
        "Rue des Glycines. Rentre la Kangoo au garage.",
    ], RETOUR_LENT, pensees=[None, "Tout Lyon rentre en même temps que moi.", None, None], ev=[None, ["embouteillage"], ["embouteillage"], None],
        extra={0: {"sortie": "cour-epicerie", "objets": mvs(DEPART_BOUTIQUE)}}), lieu=TRAJET)

    # ------------------------------------------------------------ soirée
    j.seg("19:35", "Dîner avec Josiane", "cuisine", "rt-repas", "eveille", "repos", "assis", [
        p("Entre par le garage, pose le cabas et le journal sur la table de la cuisine, accroche sa veste et le cabas vide au portemanteau.",
          None, retour="garage", posture="debout", effets={"social": 1.0},
          objets=mvs(ARRIVEE_MAISON + [("obj-progres-0309", "dans le cabas", "cuisine / table"), ("obj-cabas-boutique", "dans sa main", "entree / portemanteau")])),
        p("Raconte sa journée à Josiane pendant qu'elle bat les œufs : la livraison, Ferrand et Perpignan, Ahmed et son 1-1.", None,
          posture="debout", effets={"social": 1.0}, ev=["moment_josiane"]),
        p("Se lave les mains, boit un grand verre d'eau, s'assoit.", None, effets={"soif": 25, "hygiene": 10}),
        p("L'omelette aux pommes de terre, un quart de baguette, un verre de côtes-du-rhône.", "Elle met de l'oignon, comme sa mère.",
          ev=["plaisir_simple"], effets={"faim": 50, "soif": 10, "social": 1.0}, consommation=ingredients(fiche, "mardi", "diner")),
        p("Le comté. Josiane parle de sa sœur, qui veut vendre sa maison de Saint-Fons.", None, effets={"social": 1.0}),
        p("Il raconte l'horloger, toujours seul.", "Josiane dit qu'il faudrait l'inviter un dimanche. Elle a raison, peut-être.",
          effets={"social": 1.0}),
        p("Débarrasse ; essuie la vaisselle.", None, posture="debout", charge="simple", effets={"social": 1.0}),
        p("Range la vaisselle.", None, posture="debout", charge="simple"),
        p("Passe aux toilettes du rez-de-chaussée.", None, piece="wc", posture="debout", charge="simple", effets={"toilettes": "vide"}),
        p("Prend Le Progrès et s'installe dans son fauteuil.", None, piece="sejour", charge="repos",
          objets=mvs([("obj-progres-0309", "cuisine / table", "sejour / table basse"), ("obj-progres-0308", "sejour / table basse", "sejour / sous la table basse")])),
        p("Allume la télévision : la fin du journal.", None, piece="sejour", app=on("television"), tele=True, mode="loisir",
          objets=mvs([("obj-telecommande", "sejour / accoudoir du fauteuil", "sejour / dans sa main")])),
    ])
    tele = ["La météo.", "Un jeu télévisé ; Josiane donne les réponses avant les candidats.", "Le jeu.", "Un film d'aventure commence.",
            "Regarde le film.", "Regarde le film.", "Somnole devant le film.", "Se réveille, regarde le film.", "Regarde le film.",
            "Josiane tricote à côté de lui.", "Regarde le film, les paupières lourdes.", "Somnole."]
    tv = []
    for k, t in enumerate(tele):
        st = p(t, None, tele=True, mode="loisir", effets={"social": 1.0})
        if k == 1:
            st["ev"] = ["rire"]
        if k == 6:
            st["pensee"] = "Demain, le match. Ahmed dit 1-1. Ahmed dit toujours 1-1."
            st["ev"] = ["anticipation_plaisir"]
        tv.append(st)
    tv.append(p("Éteint la télévision : il dort debout. Josiane rallume pour finir le film : « Monte, va. Tu as dormi six heures. »",
                "Elle a raison. Au lit.", app=off("television"), mode="eveille", effets={"social": 1.0},
                objets=mvs([("obj-telecommande", "sejour / dans sa main", "sejour / accoudoir du fauteuil")])))
    j.seg("20:30", "Télévision", "sejour", "rt-soir", "loisir", "repos", "assis", tv)

    # ------------------------------------------------------------ coucher
    j.seg("21:35", "Toilette du soir", "salle-de-bain", "rt-soir", "eveille", "simple", "debout", [
        p("Monte à l'étage. Passe aux toilettes.", None, effets={"toilettes": "vide"}),
        p("Se brosse les dents, boit un verre d'eau au lavabo.", None, effets={"hygiene": 10, "soif": 15}),
        p("Prépare ses vêtements de demain sur le tabouret, enfile son pyjama.", None),
        p("Pose sa Seiko et ses lunettes sur la table de chevet.", None, piece="chambre",
          objets=mvs([("obj-montre", "poignet gauche", "chambre / table de chevet de Robert"),
                      ("obj-lunettes", "sur son front", "chambre / table de chevet de Robert")])),
        p("Se couche ; le lit est froid du côté de Josiane.", "Demain soir, le Bernabéu.", piece="chambre", posture="allongé", charge="repos"),
    ])
    j.seg("22:00", "Endormissement", "chambre", "rt-soir", "eveille", "repos", "allongé", [
        p("Éteint la lampe de chevet.", None, app=off("lumiere-chambre")),
        p("Entend la télévision en bas, très loin.", None),
        p("S'endort.", None, charge="sommeil"),
    ])
    j.seg("22:15", "Sommeil", "chambre", "sommeil", "sommeil", "sommeil", "allongé", nuit([
        ("22:15", "22:30", "léger", None, None),
        ("22:30", "23:30", "profond", None, None),
        ("23:30", "23:40", "léger", None, None),
        ("23:40", "23:45", "micro-éveil", None, None, "Josiane se couche ; il se retourne et se rendort."),
        ("23:45", "24:00", "paradoxal", "Le grossiste livre des cagettes de montres ; l'horloger les remonte une à une dans la réserve.", None),
    ]))
    j.ecarts = ["Nuit écourtée par le cinéma de la veille : six heures de sommeil.",
                "21:30 : épuisé (énergie sous le seuil d'alerte), il éteint la télévision et se couche une demi-heure plus tôt que d'habitude."]
    j.bilan = [f"**Livraison du grossiste** : {nb_lignes} lignes.",
               f"**Recette** : {euros(recette)} ({mag.comptoir.nb_clients} clients).",
               "**L'horloger** est passé : 2,10 € en espèces.",
               "**Pour la maison** : une baguette, des œufs, un oignon, des tomates."]
    return j
