"""Mercredi 10 mars 2010 — contenu rédigé de la journée de Robert Chazal.

Journée d'ouverture sans livraison du grossiste. Toute la journée, on parle
du match du soir au comptoir. Les étudiantes du 7 demandent crédit jusqu'à
vendredi. Le soir, Robert rapporte de quoi faire les croque-monsieur ;
Josiane regarde la première mi-temps avec lui puis monte se coucher. Lyon
égalise à la 75e minute et se qualifie : Robert met longtemps à s'endormir.
"""
import json
import os

from commun import (ALLER, ARRIVEE_BOUTIQUE, ARRIVEE_MAISON, BOUTIQUE, DEPART_BOUTIQUE, KANGOO, RETOUR, RETOUR_LENT, TRAJET, Magasin,
                    en_voiture, euros, ingredients, mvs, nuit)
from moteur import Journee, c, off, on, onoff, p

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")


def rediger(etat):
    fiche = json.load(open(os.path.join(RACINE, "data", "personnages", "robert-chazal.json")))
    match = json.load(open(os.path.join(RACINE, "data", "monde", "evenements.json")))["match-real-lyon"]
    j = Journee("2010-03-10", "mercredi", extinction="23:00", endormissement=45)
    mag = Magasin(fiche, etat, "2010-03-10", "mercredi")

    # ------------------------------------------------------------ nuit
    j.seg("00:00", "Nuit de mardi à mercredi", "chambre", "sommeil", "sommeil", "sommeil", "allongé", nuit([
        ("00:00", "00:10", "paradoxal", None, None),
        ("00:10", "00:25", "léger", None, None),
        ("00:25", "01:15", "profond", None, None),
        ("01:15", "01:30", "léger", None, None),
        ("01:30", "01:50", "paradoxal", "Il marque un but au Bernabéu en blouse grise, et le stade entier chante « La Bohème ».", None),
        ("01:50", "02:05", "léger", None, None),
        ("02:05", "02:45", "profond", None, None),
        ("02:45", "03:05", "léger", None, None),
        ("03:05", "03:30", "paradoxal", "Claire petite, debout sur une cagette derrière le comptoir, rend la monnaie en riant.", "reve_souvenir"),
        ("03:30", "03:35", "micro-éveil", None, None),
        ("03:35", "04:00", "léger", None, None),
        ("04:00", "04:20", "profond", None, None),
        ("04:20", "04:50", "léger", None, None),
        ("04:50", "05:15", "paradoxal", None, None),
        ("05:15", "05:30", "léger", None, None),
    ]))

    # ------------------------------------------------------------ matin
    j.seg("05:30", "Réveil", "chambre", "rt-mercredi", "eveille", "repos", "assis", [
        p("Le réveil sonne. Il l'arrête, s'assoit au bord du lit, attache sa Seiko et prend ses lunettes.",
          "Mercredi. Ce soir, le Bernabéu.", ev=["reveil_sonnerie", "anticipation_plaisir"],
          objets=mvs([("obj-montre", "chambre / table de chevet de Robert", "poignet gauche"),
                      ("obj-lunettes", "chambre / table de chevet de Robert", "sur son front")])),
    ])
    j.seg("05:35", "Toilette", "salle-de-bain", "rt-mercredi", "eveille", "simple", "debout", [
        p("Passe aux toilettes de la salle de bain.", None, effets={"toilettes": "vide"}),
        p("Douche, en sifflotant tout bas l'hymne de la Ligue des champions.", None, effets={"hygiene": 75}, ev=["plaisir_simple"]),
        p("Se rase.", None, charge="precision"),
        p("S'habille avec les vêtements préparés sur le tabouret.", None),
    ])
    j.seg("05:55", "Petit-déjeuner", "cuisine", "rt-mercredi", "eveille", "cuisine", "debout", [
        p("Descend à la cuisine, met la cafetière en route et la radio tout bas, beurre deux tartines.", None,
          app=on("cafetiere-maison", "radio-cuisine"), radio=True),
        p("Mange debout contre le buffet ; café sucré, tartines, comprimé avec un verre d'eau.", "RTL parle déjà de Madrid.", charge="repos",
          radio=True, effets={"faim": 40, "soif": 30, "cafe": True}, consommation=ingredients(fiche, None, "petit_dejeuner"), ev=["plaisir_simple"]),
        p("Rince son bol, verse le café dans le thermos pour Josiane, éteint la radio et la cafetière.", None,
          app=off("cafetiere-maison", "radio-cuisine")),
    ])
    j.seg("06:10", "Départ", "garage", "rt-mercredi", "eveille", "simple", "debout", [
        p("Prend sa veste, ses clés, celles de la Kangoo, son portefeuille et le cabas au portemanteau. Ouvre la porte basculante.", None,
          objets=mvs([("obj-veste", "entree / portemanteau", "porté"), ("obj-cles", "entree / vide-poche", "poche de la veste"),
                      ("obj-cles-kangoo", "entree / vide-poche", "dans sa main"), ("obj-portefeuille", "entree / vide-poche", "poche de la veste"),
                      ("obj-cabas-boutique", "entree / portemanteau", "dans sa main")])),
    ])
    j.seg("06:15", "Route vers la Croix-Rousse", KANGOO, "rt-mercredi", "eveille", "conduite", "assis", en_voiture([
        "Sort la Kangoo, éteint le garage, referme. Cours Émile-Zola, vide.",
        "Pont Winston-Churchill. Il fredonne.",
        "Montée de la Boucle, boulevard, cour de l'épicerie.",
    ], ALLER, ev=[["conduite_tranquille"], None, None],
        extra={0: {"objets": mvs([("obj-kangoo", "garage / place de la Kangoo", "en route"), ("obj-cles-kangoo", "dans sa main", "contact de la Kangoo")]),
                   "app": off("lumiere-garage")}}), lieu=TRAJET)

    # ------------------------------------------------------------ boutique : arrivée et pain
    pain = {"baguette": 70, "pain_campagne": 6}
    invendus = {k: mag.stock[k] for k in pain}
    j.seg("06:30", "Arrivée à la boutique", "arriere-boutique", "rt-mercredi", "eveille", "simple", "debout", [
        p("Gare la Kangoo dans la cour, entre par la porte de derrière, accroche sa veste et le cabas, enfile sa blouse.", None,
          retour="cour-epicerie", objets=mvs(ARRIVEE_BOUTIQUE + [("obj-cabas-boutique", "dans sa main", "arriere-boutique / patère")])),
    ], lieu=BOUTIQUE)
    j.seg("06:35", "Livraison du pain", "boutique", "rt-mercredi", "eveille", "simple", "debout", [
        p("Allume la boutique, lève le rideau à mi-hauteur. Le livreur de la boulangerie pose les panières et Le Progrès, reprend le pain de "
          "campagne d'hier. Robert met de côté une baguette pour la maison.", "Le Progrès fait sa une sur Madrid. Évidemment.", via=["trottoir"],
          app=on("lumiere-boutique"), livraisons=mag.livrer(pain), reprises=mag.reprendre(invendus, "invendus de la veille repris par le livreur"),
          prelevements=[mag.pour_maison("pain", 1)],
          nouveaux_objets=[{"id": "obj-progres-0310", "nom": "Le Progrès du mercredi 10 mars 2010", "position": "boutique / comptoir"}]),
    ], lieu=BOUTIQUE)
    j.seg("06:40", "Mise en rayon", "boutique", "rt-mercredi", "travail", "simple", "debout", [
        p("Remplit l'étal de fruits depuis la réserve.", None, via=["reserve"]),
        p("Range les yaourts et le lait dans la vitrine réfrigérée, les dates courtes devant.", None, via=["reserve"]),
        p("Lit la une du Progrès, appuyé au comptoir.", "« L'OL au pied du mur. » Ils écrivent toujours ça.", ev=["lecture_journal"]),
    ], lieu=BOUTIQUE)
    j.seg("06:55", "Ouverture", "boutique", "rt-mercredi", "eveille", "simple", "debout", [
        p("Lève le rideau de fer, allume la radio et la caisse, compte le fond de caisse.", None, via=["trottoir"], app=on("radio-boutique", "caisse"),
          radio=True),
    ], lieu=BOUTIQUE)

    # ------------------------------------------------------------ matinée
    vide_matin = [
        "Range les packs de lait dans la vitrine réfrigérée.",
        "Essuie le comptoir.",
        "Redresse les cagettes de l'étal.",
        "Regarde la Grande-Rue s'éveiller.",
        "Aligne les boîtes de conserve.",
        "Fait la monnaie dans le tiroir de la caisse.",
        "Chantonne avec la radio.",
        "Range les bocaux de bonbons : c'est mercredi, les gamins viendront.",
    ]
    notes_matin = {
        "07:15": {"pensee": "Un client sur deux me parle du match. Et ils disent tous 2-0 pour Madrid."},
        "07:40": {"action": "À un client qui lui demande son pronostic, il répond « 1-1 », comme Ahmed.", "ev": ["rire"]},
        "08:15": {"pensee": "La copropriété. Elle y va pour parler, pas pour voter."},
        "08:45": {"pensee": "Josiane voulait un manteau, à Noël. J'ai pris des gants. Le 16, faut faire mieux.", "ev": ["anniversaire_mariage"]},
        "09:30": {"action": "Passe aux toilettes du fond, se fait un café dans l'arrière-boutique et revient au comptoir avec la tasse de Lucas.",
                  "via": ["wc-boutique", "arriere-boutique"], "effets": {"toilettes": "vide", "cafe": True, "soif": 15},
                  "consommation": [c("cafe_boutique", 7)], "app": onoff(["cafetiere-boutique"], ["cafetiere-boutique"]), "ev": ["plaisir_simple"],
                  "objets": mvs([("obj-tasse-boutique", "arriere-boutique / évier", "boutique / comptoir")])},
        "10:10": {"action": "Lit Le Progrès entre deux clients : les deux pages sur Madrid, les régionales.", "ev": ["lecture_journal"]},
        "10:30": {"action": "Des gamins du mercredi achètent des bonbons avec leurs pièces ; il ajoute un caramel pour chacun.", "ev": ["plaisir_simple"],
                  "pensee": "Lucas fait pareil, avec ses pièces. Il compte tout deux fois."},
        "11:00": {"action": "Boit un grand verre d'eau à l'évier de l'arrière-boutique.", "via": ["arriere-boutique"], "effets": {"soif": 25}},
        "11:40": {"pensee": "Josiane fait le poulet basquaise. Les tomates d'hier soir."},
        "11:50": {"action": "Commence à resserrer l'étal de fruits avant midi."},
    }
    j.seg("07:00", "Boutique ouverte", "boutique", "rt-mercredi", "travail", "service", "debout",
          mag.service("07:00", "12:00", "Boutique ouverte", "rt-mercredi", vide_matin, notes_matin), lieu=BOUTIQUE)

    # ------------------------------------------------------------ midi
    recette_matin = mag.recette()
    argent_midi, especes_midi = mag.vider_caisse()
    j.seg("12:00", "Fermeture de midi", "boutique", "rt-mercredi", "eveille", "simple", "debout", [
        p("Baisse le rideau de fer, éteint la radio et la caisse.", None, via=["trottoir"], app=off("radio-boutique", "caisse")),
        p(f"Compte la caisse du matin dans l'arrière-boutique : {euros(especes_midi)} en espèces, rangés dans la sacoche du coffre. Rince la tasse.",
          f"{euros(recette_matin)} ce matin.", piece="arriere-boutique", charge="precision", argent=argent_midi, app=off("lumiere-boutique"),
          objets=mvs([("obj-tasse-boutique", "boutique / comptoir", "arriere-boutique / évier")])),
    ], lieu=BOUTIQUE)
    j.seg("12:10", "Retour déjeuner", KANGOO, "rt-mercredi", "eveille", "conduite", "assis", en_voiture([
        "Raccroche sa blouse, remet sa veste, sort par la cour. Descend la montée de la Boucle.",
        "Pont Winston-Churchill.",
        "Cours Émile-Zola, rue des Glycines ; rentre la Kangoo au garage.",
    ], RETOUR, ev=[None, ["conduite_tranquille"], None],
        extra={0: {"sortie": "cour-epicerie", "objets": mvs(DEPART_BOUTIQUE)}}), lieu=TRAJET)
    j.seg("12:25", "Déjeuner avec Josiane", "cuisine", "rt-repas", "eveille", "repos", "assis", [
        p("Entre par le garage, accroche sa veste, pose ses clés et son portefeuille. Ça sent le poivron dans toute la maison.", None,
          retour="garage", posture="debout", objets=mvs(ARRIVEE_MAISON), effets={"social": 1.0}),
        p("Se lave les mains, boit un verre d'eau, s'assoit.", None, effets={"soif": 20, "hygiene": 10}),
        p("Mangent le poulet basquaise avec du riz.", "Le poulet basquaise du mercredi. Depuis trente ans.", ev=["moment_josiane", "plaisir_simple"],
          effets={"faim": 55, "social": 1.0}, consommation=ingredients(fiche, "mercredi", "dejeuner")),
        p("Josiane : « Ce soir, des croque-monsieur devant ton match. Rapporte du jambon et du gruyère râpé. Et du riz pour demain. »",
          "Jambon, râpé, riz. Jambon, râpé, riz.", effets={"social": 1.0}),
        p("Lui promet de ne pas crier si Lyon marque. Elle ne le croit pas.", None, effets={"social": 1.0}, ev=["rire"]),
        p("Une orange en dessert.", None, effets={"social": 1.0, "faim": 5}),
        p("Se fait un café et le boit debout à la fenêtre.", None, posture="debout", charge="cuisine",
          effets={"cafe": True, "soif": 10}, app=onoff(["cafetiere-maison"], ["cafetiere-maison"]), consommation=[c("cafe_moulu", 7)]),
        p("Passe aux toilettes du rez-de-chaussée.", None, piece="wc", posture="debout", charge="simple", effets={"toilettes": "vide"}),
        p("S'installe dans son fauteuil.", None, piece="sejour", charge="repos"),
    ])
    j.seg("13:10", "Sieste", "sejour", "rt-repos", "sieste", "sommeil", "assis", [
        p("Ferme les yeux dans le fauteuil."),
        p("Somnole."),
        p("Somnole."),
    ])
    j.seg("13:25", "Départ", "garage", "rt-mercredi", "eveille", "simple", "debout", [
        p("Se lève, prend sa veste, ses clés et son portefeuille, ouvre le garage.", None,
          objets=mvs([("obj-veste", "entree / portemanteau", "porté"), ("obj-cles", "entree / vide-poche", "poche de la veste"),
                      ("obj-cles-kangoo", "entree / vide-poche", "dans sa main"), ("obj-portefeuille", "entree / vide-poche", "poche de la veste")])),
    ])
    j.seg("13:30", "Retour à la boutique", KANGOO, "rt-mercredi", "eveille", "conduite", "assis", en_voiture([
        "Sort la Kangoo, éteint le garage. Cours Émile-Zola.",
        "Pont Winston-Churchill.",
        "Montée de la Boucle, boulevard, cour de l'épicerie.",
    ], ALLER, extra={0: {"objets": mvs([("obj-kangoo", "garage / place de la Kangoo", "en route"),
                                        ("obj-cles-kangoo", "dans sa main", "contact de la Kangoo")]), "app": off("lumiere-garage")}}), lieu=TRAJET)
    j.seg("13:45", "Réouverture", "arriere-boutique", "rt-mercredi", "eveille", "simple", "debout", [
        p("Entre par la cour, accroche sa veste, enfile sa blouse.", None, retour="cour-epicerie", objets=mvs(ARRIVEE_BOUTIQUE)),
        p("Allume la boutique, remplit l'étal de pommes depuis la réserve.", None, piece="boutique", via=["reserve"], app=on("lumiere-boutique")),
        p("Lève le rideau, rallume la radio et la caisse.", None, piece="boutique", via=["trottoir"], app=on("radio-boutique", "caisse"), radio=True),
    ], lieu=BOUTIQUE)

    # ------------------------------------------------------------ après-midi
    vide_apres = [
        "Range la réserve.",
        "Recopie les ventes du matin dans le cahier.",
        "Regarde passer les enfants qui sortent du centre de loisirs.",
        "Redresse les boîtes de conserve.",
        "Essuie la vitrine réfrigérée.",
        "Chantonne avec la radio.",
        "Écrit une étiquette « Tomates de pays ».",
        "Aplatit les cartons vides dans la réserve.",
    ]
    notes_apres = {
        "14:10": {"pensee": "Sept heures encore. Le temps passe pas, les jours de match."},
        "14:40": {"action": "M. Garnier a scotché l'affiche du match dans sa vitrine ; Robert sort la regarder et ils en rient sur le trottoir.",
                  "via": ["trottoir"], "ev": ["bavardage_voisin", "rire"], "effets": {"social": 2}},
        "15:00": {"action": "Boit un verre d'eau à l'arrière-boutique.", "via": ["arriere-boutique"], "effets": {"soif": 25}},
        "15:30": {"pensee": "Claire a dit que Lucas voulait un maillot de l'OL. Pour ses sept ans, peut-être.", "ev": ["pensee_claire"]},
        "16:00": {"action": "Les Grosses Têtes commencent à la radio ; il monte le son.", "ev": ["plaisir_simple"]},
        "16:30": {"action": "Se fait un café dans l'arrière-boutique et le boit au comptoir.", "via": ["arriere-boutique"],
                  "effets": {"cafe": True, "soif": 15}, "consommation": [c("cafe_boutique", 7)],
                  "app": onoff(["cafetiere-boutique"], ["cafetiere-boutique"]),
                  "objets": mvs([("obj-tasse-boutique", "arriere-boutique / évier", "boutique / comptoir")])},
        "16:50": {"action": "Rit tout seul à une histoire de Bouvard ; une cliente rit avec lui.", "ev": ["rire"]},
        "17:15": {"action": "Passe aux toilettes du fond pendant un creux.", "via": ["wc-boutique"], "effets": {"toilettes": "vide"}},
        "17:45": {"action": "Boit un verre d'eau.", "via": ["arriere-boutique"], "effets": {"soif": 20}},
        "18:05": {"apres": "Il sort le carnet des ardoises de sous la caisse et y note la date et la somme.",
                  "pensee": "Elles paieront. Elles paient toujours, celles-là."},
        "18:30": {"pensee": "Deux heures un quart. Je ferme, je roule, je mange, et c'est le coup d'envoi.", "ev": ["anticipation_plaisir"]},
        "18:50": {"action": "Commence à rentrer l'étal de fruits pour la nuit."},
    }
    j.seg("14:00", "Boutique ouverte", "boutique", "rt-mercredi", "travail", "service", "debout",
          mag.service("14:00", "19:00", "Boutique ouverte", "rt-mercredi", vide_apres, notes_apres), lieu=BOUTIQUE)

    # ------------------------------------------------------------ fermeture
    recette = mag.recette()
    argent_soir, especes_soir = mag.vider_caisse()
    cabas = [mag.pour_maison("jambon", 1), mag.pour_maison("fromage_rape", 1), mag.pour_maison("riz", 1)]
    j.seg("19:00", "Fermeture", "boutique", "rt-mercredi", "eveille", "simple", "debout", [
        p("Rentre l'étal, baisse le rideau de fer, ferme à clé, éteint la radio et la caisse.", None, via=["trottoir"],
          app=off("radio-boutique", "caisse")),
        p(f"Compte la caisse au bureau : {euros(especes_soir)} en espèces depuis midi, rangés dans la sacoche du coffre. La caisse tombe juste. "
          f"La journée fait {euros(recette)}.", "Juste en dessous de trois cents. Comme d'habitude, maintenant." if recette < 300 else
          "Au-dessus de trois cents. Les jours de match, les gens ont faim.", piece="arriere-boutique", charge="precision", posture="assis",
          argent=argent_soir, ev=["caisse_juste"] + (["constat_chiffre"] if recette < 300 else []),
          objets=mvs([("obj-tasse-boutique", "boutique / comptoir", "arriere-boutique / évier")])),
        p("Remplit le cabas : une barquette de jambon, un sachet d'emmental râpé, un paquet de riz. Glisse Le Progrès dessus, éteint la boutique.",
          "Jambon, râpé, riz. Tout y est.", piece="arriere-boutique", prelevements=cabas, app=off("lumiere-boutique"),
          objets=mvs([("obj-cabas-boutique", "arriere-boutique / patère", "dans sa main"), ("obj-progres-0310", "boutique / comptoir", "dans le cabas")])),
    ], lieu=BOUTIQUE)
    j.seg("19:15", "Retour à la maison", KANGOO, "rt-mercredi", "eveille", "conduite", "assis", en_voiture([
        "Raccroche sa blouse, remet sa veste, sort par la cour. Descend la montée de la Boucle.",
        "Pont Winston-Churchill. Des drapeaux de l'OL aux fenêtres des voitures.",
        "Boulevard de Stalingrad, cours Émile-Zola, au pas.",
        "Rue des Glycines. Rentre la Kangoo au garage.",
    ], RETOUR_LENT, pensees=[None, "Tout le monde rentre voir le match.", None, None], ev=[None, ["anticipation_plaisir"], ["embouteillage"], None],
        extra={0: {"sortie": "cour-epicerie", "objets": mvs(DEPART_BOUTIQUE)}}), lieu=TRAJET)

    # ------------------------------------------------------------ soirée
    j.seg("19:35", "Retour à la maison", "cuisine", "rt-repas", "eveille", "simple", "debout", [
        p("Entre par le garage, pose le cabas et le journal sur la table de la cuisine, accroche sa veste et le cabas vide au portemanteau.",
          None, retour="garage", effets={"social": 1.0},
          objets=mvs(ARRIVEE_MAISON + [("obj-progres-0310", "dans le cabas", "cuisine / table"), ("obj-cabas-boutique", "dans sa main", "entree / portemanteau")])),
        p("Raconte sa journée à Josiane : les ardoises des étudiantes, les gamins et les bonbons.", "Elle dit que je fais trop crédit. Elle a raison.",
          effets={"social": 1.0}, ev=["moment_josiane"]),
        p("Passe aux toilettes du rez-de-chaussée, se lave les mains, boit un grand verre d'eau.", None, piece="cuisine", via=["wc"],
          effets={"toilettes": "vide", "hygiene": 10, "soif": 25}),
    ])
    j.seg("19:50", "Le Progrès avant le match", "sejour", "rt-soir", "lecture", "lecture", "assis", [
        p("S'installe dans son fauteuil avec Le Progrès, les lunettes sur le nez.", None, ev=["lecture_journal"],
          objets=mvs([("obj-progres-0310", "cuisine / table", "sejour / dans sa main"), ("obj-lunettes", "sur son front", "sur son nez"),
                      ("obj-progres-0309", "sejour / table basse", "sejour / sous la table basse")])),
        p("Relit les deux pages sur Madrid.", "Il faut marquer là-bas. Un but, et c'est fait."),
        p("Lit les résultats du tiercé et la page des régionales.", None),
        p("Fait les mots fléchés du journal.", None),
        p("Pose le journal, remonte ses lunettes. Allume la télévision : l'avant-match.", None, mode="loisir", tele=True, app=on("television"),
          objets=mvs([("obj-progres-0310", "sejour / dans sa main", "sejour / table basse"), ("obj-lunettes", "sur son nez", "sur son front"),
                      ("obj-telecommande", "sejour / accoudoir du fauteuil", "sejour / dans sa main")]), ev=["anticipation_plaisir"]),
        p("Les consultants refont l'histoire du match aller : 1-0 à Gerland.", None, mode="loisir", tele=True),
        p("Va chercher une bière au réfrigérateur et deux verres.", None, mode="eveille", tele=True, via=["cuisine"], posture="debout"),
        p("L'avant-match ; il ne tient pas en place.", None, mode="loisir", tele=True),
    ])
    j.seg("20:30", "Croque-monsieur devant l'avant-match", "sejour", "rt-soir", "loisir", "repos", "assis", [
        p("Josiane apporte les croque-monsieur sur des plateaux ; ils mangent devant la télévision, lui avec sa bière.",
          "Des croque devant le foot. Comme en 98.", tele=True, ev=["moment_josiane", "plaisir_simple"], effets={"faim": 45, "soif": 15, "social": 1.0},
          consommation=ingredients(fiche, "mercredi", "diner")),
        p("Finit son croque-monsieur. Les équipes entrent sur la pelouse du Bernabéu.", None, tele=True, effets={"social": 1.0}),
        p("Les hymnes. Josiane s'installe sur le canapé avec son tricot.", None, tele="match", effets={"social": 1.0}),
    ])

    # ------------------------------------------------------------ le match
    moments = {m["heure"]: m for m in match["moments"]}
    reactions = {"but_adverse": " Robert tape du poing sur l'accoudoir. Josiane ne lève pas les yeux de son tricot.",
                 "but_equipe": " Robert se lève d'un bond en criant, puis se plaque la main sur la bouche : Josiane dort au-dessus.",
                 "qualification_equipe": " Robert reste debout devant l'écran, les bras levés, sans un bruit."}
    pas_match = []
    en_pause = False
    for k in range(int((22 * 60 + 40 - (20 * 60 + 45)) / 5)):
        h = f"{(20 * 60 + 45 + 5 * k) // 60:02d}:{(20 * 60 + 45 + 5 * k) % 60:02d}"
        m = moments.get(h)
        avec_josiane = h < "21:35"
        eff = {"social": 1.0} if avec_josiane else {}
        if m:
            en_pause = bool(m.get("pause"))
            st = p(m["texte"] + reactions.get(m.get("ev"), ""), None, tele="match", ev=[m["ev"]] if m.get("ev") else [], effets=eff)
            if m.get("ev") == "but_equipe":
                st["pensee"] = "Pjanić ! Pjanić ! Doucement… Pjanić."
            if m.get("ev") == "but_adverse":
                st["pensee"] = "Ronaldo. Six minutes. Ça commence bien."
            if m.get("fin"):
                st["pensee"] = "Qualifiés. Au Bernabéu. Ahmed va être insupportable."
        elif h == "21:35":
            st = p("Mi-temps. Josiane plie son tricot et monte se coucher : « Réveille-moi s'ils gagnent. Ou pas, d'ailleurs. » Il passe aux toilettes "
                   "et se sert un verre d'eau.", None, tele="match", piece="sejour", via=["wc", "cuisine"], effets={"toilettes": "vide", "soif": 20},
                   posture="debout", mode="eveille")
        elif en_pause:
            st = p("La mi-temps ; les consultants refont la première période.", None, tele="match", effets=eff)
        else:
            st = p("Suit le match, penché en avant, les coudes sur les genoux." if k % 3 else "Suit le match ; Lyon subit.", None, tele="match",
                   ev=["match_tension"], effets=eff)
        pas_match.append(st)
    j.seg("20:45", "Real Madrid – Lyon", "sejour", "rt-soir", "loisir", "repos", "assis", pas_match)
    j.seg("22:40", "Après le match", "sejour", "rt-soir", "eveille", "simple", "debout", [
        p("Éteint la télévision, range les verres à la cuisine. Il a encore les mains qui tremblent.", None, app=off("television"),
          via=["cuisine"], ev=["souvenir_excitant"],
          objets=mvs([("obj-telecommande", "sejour / dans sa main", "sejour / accoudoir du fauteuil")])),
    ])

    # ------------------------------------------------------------ coucher
    j.seg("22:45", "Toilette du soir", "salle-de-bain", "rt-soir", "eveille", "simple", "debout", [
        p("Éteint le séjour, monte sans bruit. Passe aux toilettes, se brosse les dents, boit un verre d'eau.", None,
          effets={"toilettes": "vide", "hygiene": 10, "soif": 15}),
        p("Prépare ses vêtements de demain, enfile son pyjama.", None),
        p("Pose sa Seiko et ses lunettes sur la table de chevet, se glisse dans le lit.", "Pjanić. À la 75e. Je l'oublierai pas, celle-là.",
          piece="chambre", posture="allongé", charge="repos", ev=["souvenir_excitant"],
          objets=mvs([("obj-montre", "poignet gauche", "chambre / table de chevet de Robert"),
                      ("obj-lunettes", "sur son front", "chambre / table de chevet de Robert")])),
    ])
    j.seg("23:00", "Endormissement", "chambre", "rt-soir", "eveille", "repos", "allongé", [
        p("Éteint la lampe de chevet.", None, app=off("lumiere-chambre")),
        p("Revoit le but de Pjanić, les yeux ouverts dans le noir.", None, ev=["souvenir_excitant"]),
        p("Se retourne. Le cœur bat encore.", None),
        p("Pense à Ahmed, demain, à ce qu'il va dire.", None),
        p("Se retourne de l'autre côté. Josiane soupire dans son sommeil.", None),
        p("Compte les cagettes de la livraison de vendredi pour s'endormir.", None),
        p("Se calme peu à peu.", None),
        p("Les paupières lourdes.", None),
        p("S'endort.", None, charge="sommeil"),
    ])
    j.seg("23:45", "Sommeil", "chambre", "sommeil", "sommeil", "sommeil", "allongé", nuit([
        ("23:45", "24:00", "léger", None, None),
    ]))
    j.ecarts = ["Soirée de match : dîner devant la télévision à 20:30, coucher à 23:00.",
                "Endormissement en 45 minutes : l'excitation de la qualification."]
    j.bilan = [f"**Recette** : {euros(recette)} ({mag.comptoir.nb_clients} clients).",
               "**Ardoise** : les étudiantes du 7 ont pris à crédit jusqu'à vendredi.",
               "**Pour la maison** : une baguette, du jambon, de l'emmental râpé, du riz.",
               "**Real Madrid – Lyon, 1-1** : Lyon qualifié pour les quarts de finale ; Josiane est montée à la mi-temps."]
    return j
