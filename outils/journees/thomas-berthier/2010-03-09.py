"""Mardi 9 mars 2010 — contenu rédigé de la journée de Thomas Berthier.

Course à pied le matin (escalier, pentes, quais de Saône), révision de la
Rolex, montres à quartz, validation de l'Omega, puis deuxième séance sur
l'axe de la montre de son grand-père : les pivots.
"""
from moteur import Journee, c, pr, course, idx, marche, mv, off, on, onoff, p


def rediger():
    j = Journee("2010-03-09", "mardi", extinction="22:15")

    # ------------------------------------------------------------ nuit
    # Endormi à 23:15 la veille : cycles de 90 minutes à partir de 23:15.
    CYCLES = [
        ("00:00", "00:30", "profond", None, None),
        ("00:30", "00:45", "paradoxal", "L'axe tourne sur le tour, mais le copeau ne s'arrête plus de sortir.", None),
        ("00:45", "00:55", "léger", None, None),
        ("00:55", "01:40", "profond", None, None),
        ("01:40", "01:55", "léger", None, None),
        ("01:55", "02:15", "paradoxal", "Une soupe déborde de la marmite ; il cherche le bouton de la plaque sans le trouver.", None),
        ("02:15", "02:25", "léger", None, None),
        ("02:25", "02:55", "profond", None, None),
        ("02:55", "03:15", "léger", None, None),
        ("03:15", "03:45", "paradoxal", "Un train vers Besançon. Son père est assis en face de lui et regarde par la fenêtre sans parler.", "reve_inquiet"),
        ("03:45", "04:05", "léger", None, None),
        ("04:05", "04:20", "profond", None, None),
        ("04:20", "04:45", "léger", None, None),
        ("04:45", "05:15", "paradoxal", "Il compte les marches d'un escalier qui monte toujours, sans palier.", None),
        ("05:15", "05:35", "léger", None, None),
        ("05:35", "05:45", "profond", None, None),
        ("05:45", "06:10", "léger", None, None),
        ("06:10", "06:40", "paradoxal", "Le quai de la Saône au petit matin ; l'eau est immobile comme du verre.", None),
        ("06:40", "07:00", "léger", None, None),
    ]
    nuit = []
    for d, f, phase, reve, ev in CYCLES:
        for k, _ in enumerate(range(idx(d), idx(f))):
            nuit.append(p("Dort.", phase_sommeil=phase, reve=reve, ev=[ev] if (ev and k == 0) else []))
    j.seg("00:00", "Nuit de lundi à mardi", "chambre", "sommeil", "sommeil", "sommeil", "allongé", nuit)

    # ------------------------------------------------------------ matin et course
    j.seg("07:00", "Réveil", "chambre", "rt-matin-course", "eveille", "repos", "allongé", [
        p("La sonnerie retentit. Il l'éteint, allume la lampe de chevet et s'assoit au bord du lit.",
          "Des marches qui montent toujours. Normal, c'est le jour de la course.", ev=["reveil_sonnerie"], app=on("lumiere-chambre")),
    ])
    j.seg("07:05", "Toilettes et verre d'eau", "salle-de-bain", "rt-matin-course", "eveille", "simple", "debout", [
        p("Passe aux toilettes, puis boit un grand verre d'eau au lavabo.", "Boire avant de courir. Toujours.",
          via=["wc"], effets={"toilettes": "vide", "soif": 20}),
    ])
    j.seg("07:10", "Tenue de course", "chambre", "rt-matin-course", "eveille", "simple", "debout", [
        p("Enfile son collant, son tee-shirt technique, son coupe-vent et son bonnet.", "Le collant est froid. Il le sera moins dans dix minutes.",
          objets=[mv("obj-tenue-course", "chambre / armoire, étagère du bas", "porté")]),
    ])
    j.seg("07:15", "Départ", "entree", "rt-matin-course", "eveille", "simple", "debout", [
        p("Passe à la cuisine prendre le sac-poubelle et en remet un neuf. Chausse ses chaussures de course, prend ses clés, sort, ferme la porte à clé et vérifie deux fois.",
          "La poubelle sent le poulet d'hier. Elle descend avec moi.", via=["cuisine"],
          nouveaux_objets=[{"id": "obj-poubelle-2", "nom": "Sac-poubelle de la cuisine (neuf)", "position": "cuisine / poubelle sous l'évier"}],
          objets=[mv("obj-poubelle", "cuisine / poubelle sous l'évier", "dans sa main"),
                  mv("obj-chaussures-course", "entree / meuble à chaussures", "aux pieds"),
                  mv("obj-cles", "entree / vide-poche de la commode", "poche du coupe-vent")]),
    ])
    j.seg("07:20", "Descente vers la Saône", "pentes de la Croix-Rousse", "rt-matin-course", "effort", "simple", "en course", [
        p("Appuie sur la minuterie de l'escalier, descend les trois étages, dépose le sac au local poubelles et sort. Commence à courir doucement dans la descente.",
          "Soixante-six marches. Je les compte sans le vouloir, depuis quatre ans.", ev=["effort_physique"],
          sortie=True, escalier={"sens": "descente"}, parcours=[course(600, -35)],
          objets=[mv("obj-poubelle", "dans sa main", "local poubelles de l'immeuble")]),
        p("Descend les pentes en retenant ses foulées.", "À la descente, ce sont les genoux qui paient.",
          ev=["effort_physique"], parcours=[course(900, -50)]),
    ], lieu="exterieur")
    j.seg("07:30", "Course le long de la Saône", "quais de Saône", "rt-matin-course", "effort", "simple", "en course", [
        p("Rejoint le bord de l'eau et prend son rythme vers le nord.", "La Saône est lisse. Elle a la couleur du ciel.",
          ev=["effort_physique"], parcours=[course(800)]),
        p("Court en cadence régulière.", "Inspirer sur trois foulées, expirer sur deux.", ev=["effort_physique"], parcours=[course(800)]),
        p("Continue le long du quai.", "Papa courait le dimanche, avant. Avant son cœur.", ev=["effort_physique", "pensee_pere"], parcours=[course(800)]),
        p("Fait demi-tour au repère habituel.", "Demi-tour. Le retour paraît toujours plus court.", ev=["effort_physique"], parcours=[course(800)]),
        p("Revient vers le sud, le souffle installé.", "Les pivots ce soir. Deux centièmes de réserve, pour la trempe.",
          ev=["effort_physique", "anticipation_delicate"], parcours=[course(800)]),
    ], lieu="exterieur")
    j.seg("07:55", "Remontée des pentes", "pentes de la Croix-Rousse", "rt-matin-course", "effort", "simple", "en course", [
        p("Attaque la montée en courant.", "Ne pas regarder en haut.", ev=["effort_physique"], parcours=[course(600, 35)]),
        p("Passe à la marche dans la partie la plus raide.", "Je marche ici. Comme d'habitude, au même endroit.",
          ev=["effort_physique"], parcours=[marche(500, 30)], posture="en marche"),
        p("Termine la montée en marchant, reprend son souffle.", "Le cœur redescend. La tête est vide, enfin.",
          ev=["effort_physique"], parcours=[marche(400, 20)], posture="en marche"),
    ], lieu="exterieur")
    j.seg("08:10", "Retour", "entree", "rt-matin-course", "effort", "simple", "debout", [
        p("Compose le code, monte les trois étages, ouvre la porte. Pose ses clés dans le vide-poche et range ses chaussures.",
          "Soixante-six marches, les jambes lourdes. Bonne fatigue.", ev=["fin_de_course"],
          retour=True, escalier={"sens": "montee", "apres_course": True},
          objets=[mv("obj-cles", "poche du coupe-vent", "entree / vide-poche de la commode"),
                  mv("obj-chaussures-course", "aux pieds", "entree / meuble à chaussures")]),
    ])
    j.seg("08:15", "Étirements, douche et rasage", "salle-de-bain", "rt-matin-course", "eveille", "simple", "debout", [
        p("Boit un grand verre d'eau, s'étire, retire sa tenue et la met dans le panier à linge.", "Demain, la machine. Le panier sera plein.",
          effets={"soif": 20}, objets=[mv("obj-tenue-course", "porté", "salle-de-bain / panier à linge")]),
        p("Prend une douche chaude.", None, effets={"hygiene": 75}, ev=["plaisir_simple"]),
        p("Se rase.", "Rasé le mardi et le jeudi, les jours de course."),
    ])
    j.seg("08:30", "S'habille", "chambre", "rt-matin-course", "eveille", "simple", "debout", [
        p("S'habille pour l'atelier et attache sa montre.", None,
          objets=[mv("obj-montre-poignet", "chambre / table de chevet", "poignet gauche")]),
    ])
    j.seg("08:35", "Petit-déjeuner", "cuisine", "rt-matin-course", "eveille", "cuisine", "debout", [
        p("Prépare le café avec la dernière dose du paquet entamé.", "Le paquet a tenu jusqu'à ce matin. Comme prévu.",
          app=on("plaque-1"), objets=[mv("obj-cafetiere", "cuisine / égouttoir", "cuisine / plaque électrique")],
          consommation=[c("cafe_moulu", 7)]),
        p("Grille deux tranches de pain, éteint la plaque, se sert un café dans la tasse bleue.", None,
          app=off("plaque-1"), objets=[mv("obj-tasse", "cuisine / égouttoir", "cuisine / plan de travail")],
          consommation=[c("pain_tranches", 2), c("beurre", 10), c("confiture_abricot", 2)]),
        p("Mange ses tartines, un yaourt et une banane, avec un verre d'eau.", "Faim de loup, les jours de course.",
          effets={"faim": 55, "soif": 35, "cafe": True}, ev=["plaisir_simple"], posture="assis",
          consommation=[c("yaourts", 1), c("bananes", 1)]),
    ])
    j.seg("08:50", "Rangement et montre", "cuisine", "rt-matin-course", "eveille", "simple", "debout", [
        p("Rince la tasse et la cafetière. Remonte sa montre : vingt tours de couronne.", None,
          objets=[mv("obj-tasse", "cuisine / plan de travail", "cuisine / égouttoir"),
                  mv("obj-cafetiere", "cuisine / plaque électrique", "cuisine / égouttoir")]),
    ])
    j.seg("08:55", "Réglage de la montre et ouverture de l'atelier", "atelier", "rt-matin-course", "eveille", "simple", "debout", [
        p("Passe par la chambre régler sa montre sur le réveil : trois secondes d'avance. Puis allume la lampe d'établi, aligne ses outils et ouvre le coffre.",
          "Trois secondes. Hier quatre. Elle est régulière.", via=["chambre"], ev=["controle_conforme"], app=on("lampe-etabli"),
          objets=[mv("obj-cles-coffre", "atelier / tiroir de l'établi, à droite", "atelier / serrure du coffre")]),
    ])

    # ------------------------------------------------------------ matinée
    j.seg("09:00", "Rolex : démontage complet", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Chausse ses lunettes, sort la Rolex du coffre et pose le mouvement sur un porte-mouvement.", None,
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez"), mv("obj-rolex", "atelier / coffre-fort", "atelier / établi")]),
        p("Laisse le ressort se désarmer en retenant le rochet.", "Doucement. Un ressort qui se lâche d'un coup, ça casse des dents.", ev=["operation_delicate"]),
        p("Démonte le mécanisme de date : disque, sautoir, roue de quantième."),
        p("Range les pièces de date dans un compartiment du plateau."),
        p("Retire le coq et le balancier-spiral.", "Le spiral d'abord, toujours.", ev=["operation_delicate"]),
        p("Démonte le pont d'ancre et l'ancre."),
        p("Démonte le pont de rouage."),
        p("Sort la roue d'échappement, la roue de seconde, la roue moyenne."),
        p("Dépose la roue de centre."),
        p("Démonte le pont de barillet."),
        p("Sort le barillet et l'ouvre."),
        p("Extrait l'ancien ressort : il est cassé en bout.", "Fatigué ? Non, cassé. Le client a bien fait de l'apporter."),
        p("Démonte la minuterie côté cadran."),
        p("Démonte le mécanisme de remontage : tige, pignon coulant, bascule."),
        p("Inspecte la platine nue à la loupe.", "Les pierres sont saines. Pas une fissure.", ev=["controle_conforme"]),
        p("Note sur la fiche : ressort cassé, huiles sèches, aucune usure anormale.", charge="simple"),
        p("Compte les pièces dans le plateau : tout y est.", ev=["controle_conforme"]),
        p("Recouvre le plateau d'une cloche."),
    ])
    j.seg("10:30", "Pause", "wc", "rt-atelier", "eveille", "repos", "debout", [
        p("Pose ses lunettes, passe aux toilettes.", effets={"toilettes": "vide"},
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("10:35", "Pause café", "cuisine", "rt-atelier", "eveille", "repos", "debout", [
        p("Ouvre le paquet de café neuf et se fait un café.", None, app=onoff(allume=["plaque-1"], eteint=["plaque-1"]),
          consommation=[c("cafe_moulu", 7)],
          effets={"soif": 15, "cafe": True}, ev=["plaisir_simple"]),
        p("Boit un verre d'eau, s'étire.", "Le dos va bien. La course l'a délié.", effets={"soif": 20}),
    ])
    j.seg("10:45", "Rolex : nettoyage", "atelier", "rt-atelier", "travail", "simple", "debout", [
        p("Remet ses lunettes, dispose les pièces dans les paniers, le balancier à part.", None,
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Lance la machine à ultrasons : quarante minutes.", "Quarante minutes. Les quartz pendant ce temps.", app=on("machine-ultrasons")),
        p("Sort du coffre la boîte des six montres à quartz.", None,
          objets=[mv("obj-lot-quartz", "atelier / coffre-fort, dans une boîte étiquetée", "atelier / établi")]),
    ])
    j.seg("11:00", "Montres à quartz : piles et joints", "atelier", "rt-atelier", "travail", "simple", "assis", [
        p("Ouvre la première montre : pile changée, joint graissé, fond refermé."),
        p("Deuxième montre, même opération."),
        p("Troisième, une montre de dame plaquée or : le joint est fendu, il le remplace."),
        p("Quatrième et cinquième : piles seulement."),
        p("Sixième : la pile a coulé. Il nettoie les contacts à l'alcool.", "Une pile qui coule, c'est un mouvement qui souffre. Juste à temps."),
        p("Teste les six montres au contrôleur d'étanchéité, l'une après l'autre.", app=on("controleur-etancheite")),
        p("Les six tiennent la pression. La machine à ultrasons s'arrête.", "Six sur six.", ev=["controle_conforme"],
          app=off("controleur-etancheite", "machine-ultrasons")),
        p("Note les six interventions sur les fiches.", None),
    ])
    j.seg("11:40", "Rolex : contrôle des pièces", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Sort les paniers de la machine et laisse sécher les pièces sous une cloche.", posture="debout"),
        p("Contrôle les pivots du rouage à la loupe.", ev=["controle_conforme"]),
        p("Contrôle les dentures."),
        p("Contrôle l'ancre et les levées.", ev=["controle_conforme"]),
        p("Examine le balancier et le spiral : spiral plat, bien centré.", "Un spiral bien plat. Rien à reprendre.", ev=["controle_conforme"]),
        p("Nettoie le barillet et son couvercle au bois de sureau."),
        p("Sort le ressort neuf de son sachet et le compare à l'ancien.", "Même hauteur, même épaisseur. La bonne référence.",
          ev=["controle_conforme"], objets=[mv("obj-ressort-rolex", "atelier / tiroir de l'établi", "atelier / établi")]),
        p("Prépare la graisse de barillet et les huiles."),
        p("Range les pièces propres dans le plateau couvert."),
        p("Éteint la lampe, pose ses lunettes.", "Faim. Le poulet d'hier.", app=off("lampe-etabli"),
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])

    # ------------------------------------------------------------ midi
    j.seg("12:30", "Déjeuner", "cuisine", "rt-atelier", "eveille", "cuisine", "debout", [
        p("Met de l'eau à bouillir pour le riz.", None, app=on("plaque-1")),
        p("Verse le riz. Réchauffe à la poêle la cuisse de poulet et les pommes de terre d'hier.", None, app=on("plaque-2"),
          consommation=[c("riz", 80), c("poulet_roti", 1), c("pommes_de_terre_roties", 1), c("condiments", 1)]),
        p("Égoutte le riz, sert son assiette, éteint les plaques.", None, app=off("plaque-1", "plaque-2")),
        p("Déjeune à la table du séjour avec un verre d'eau.", "Le poulet est meilleur réchauffé. Grand-mère le disait.",
          piece="sejour", posture="assis", effets={"faim": 55, "soif": 20}, ev=["repas_seul", "souvenir_tendre"], charge="repos"),
        p("Termine son assiette.", "Six montres à quartz ce matin. Ça ne paie pas beaucoup, mais ça paie.", piece="sejour", posture="assis", charge="repos"),
        p("Débarrasse.", None, piece="sejour", charge="repos"),
    ])
    j.seg("13:00", "Café et vaisselle", "cuisine", "rt-atelier", "eveille", "cuisine", "debout", [
        p("Se fait un café.", app=onoff(allume=["plaque-1"], eteint=["plaque-1"]),
          consommation=[c("cafe_moulu", 7)], effets={"soif": 15, "cafe": True}, ev=["plaisir_simple"]),
        p("Lave la casserole, la poêle et l'assiette."),
        p("Essuie et range."),
        p("Rince la tasse et la cafetière."),
        p("Boit un verre d'eau.", effets={"soif": 20}),
        p("Regarde la cour par la fenêtre.", "Gris. Mars hésite."),
    ])
    j.seg("13:30", "Repos", "chambre", "rt-atelier", "eveille", "repos", "debout", [
        p("Va chercher son livre sur la table de chevet.", objets=[mv("obj-livre", "chambre / table de chevet", "dans sa main")]),
    ])
    j.seg("13:35", "Lecture", "sejour", "rt-atelier", "lecture", "lecture", "allongé", [
        p("S'allonge sur le canapé et lit.", "Ils cherchent la mer. Moi je cherche la fin du chapitre."),
        p("Lit (page 145)."),
        p("Lit (page 148)."),
        p("Ferme les yeux quelques minutes.", mode="sieste", charge="sommeil"),
    ])
    j.seg("13:55", "Rangement du livre", "chambre", "rt-atelier", "eveille", "repos", "debout", [
        p("Rapporte tout de suite le livre sur la table de chevet.", "Cette fois, il retourne à sa place tout de suite.",
          ev=["controle_conforme"], objets=[mv("obj-livre", "dans sa main", "chambre / table de chevet")]),
    ])

    # ------------------------------------------------------------ après-midi
    j.seg("14:00", "Rolex : ressort neuf, barillet, rouage", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Rallume la lampe, remet ses lunettes. Graisse les parois du barillet.", ev=["operation_delicate"], app=on("lampe-etabli"),
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Enroule le ressort neuf dans le barillet avec l'enrouloir.", "Le moment où un ressort neuf prend sa place. Il ne doit pas vriller.",
          ev=["operation_delicate"], objets=[mv("obj-ressort-rolex", "atelier / établi", "atelier / établi, monté dans le barillet de la Rolex")]),
        p("Pose l'arbre de barillet, huile, ferme le couvercle."),
        p("Vérifie le jeu de l'arbre : correct.", ev=["controle_conforme"]),
        p("Remonte le mécanisme de remontage et de mise à l'heure."),
        p("Pose le barillet sur la platine et son pont."),
        p("Pose la roue de centre.", ev=["operation_delicate"]),
        p("Pose la roue moyenne et la roue de seconde.", ev=["operation_delicate"]),
        p("Pose la roue d'échappement.", ev=["operation_delicate"]),
        p("Pose le pont de rouage et guide les pivots un par un.", ev=["operation_delicate"]),
        p("Les pivots trouvent leurs trous. Il serre les vis.", "Ils sont entrés seuls. Comme hier.", ev=["geste_reussi"]),
        p("Souffle sur le rouage : il tourne librement.", ev=["controle_conforme"]),
        p("Huile les pivots côté pont.", ev=["operation_delicate"]),
        p("Retourne le mouvement et huile les pivots côté cadran.", ev=["operation_delicate"]),
        p("Monte la minuterie."),
        p("Remonte le mécanisme de date.", "Le sautoir. Il saute toujours quand on ne regarde pas."),
        p("Fait passer la date à la main sur deux jours : correct.", ev=["controle_conforme"]),
        p("Note l'avancement sur la fiche.", "Le plus gros est fait. Demain matin, réglage et emboîtage.", charge="simple"),
    ])
    j.seg("15:30", "Pause", "wc", "rt-atelier", "eveille", "repos", "debout", [
        p("Pose ses lunettes, passe aux toilettes.", effets={"toilettes": "vide"},
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("15:35", "Pause", "cuisine", "rt-atelier", "eveille", "repos", "debout", [
        p("Boit un verre d'eau et mange une orange en regardant par la fenêtre.", None,
          consommation=[c("oranges", 1)], effets={"soif": 20, "faim": 15}, ev=["plaisir_simple"]),
    ])
    j.seg("15:40", "Rolex : échappement et balancier", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Remet ses lunettes. Pose l'ancre.", ev=["operation_delicate"],
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Pose le pont d'ancre, vérifie les ébats."),
        p("Huile les levées de l'ancre avec la pointe la plus fine de l'huilier.", ev=["operation_delicate"]),
        p("Pose le balancier-spiral.", "Le spiral, c'est un cheveu. Encore et toujours.", ev=["operation_delicate"]),
        p("Visse le pont de balancier."),
        p("Huile les pierres de balancier.", ev=["operation_delicate"]),
        p("Donne trois tours de couronne : le balancier part.", "Elle repart. Le ressort neuf pousse bien.", ev=["geste_reussi"]),
        p("Écoute le battement à la loupe : régulier."),
        p("Pose le mouvement sur le chronocomparateur.", app=on("chronocomparateur")),
        p("Premier relevé : plus 12 secondes par jour, amplitude excellente.", "Bonne amplitude. Un ressort neuf, ça se voit tout de suite."),
        p("Relevé couronne en bas : plus 15."),
        p("Laisse tourner pour que l'huilage se répartisse."),
        p("Range ses huiles.", charge="simple"),
        p("Note les mesures. Le réglage fin se fera demain matin, les huiles reposées.", "Une nuit de repos pour les huiles. Grand-père y tenait.",
          ev=["souvenir_grand_pere"], app=off("chronocomparateur"), charge="simple"),
        p("Range le mouvement dans un boîtier de protection."),
        p("Nettoie l'établi.", charge="simple"),
    ])
    j.seg("17:00", "Omega : fin de l'observation", "atelier", "rt-atelier", "travail", "simple", "assis", [
        p("Sort l'Omega du coffre et compare son heure à celle de sa montre réglée ce matin.", None,
          objets=[mv("obj-omega", "atelier / coffre-fort, remontée, en observation", "atelier / établi")]),
        p("Vingt-quatre heures d'observation : plus 4 secondes. Conforme.", "Validée. Elle partira lundi.", ev=["controle_conforme"]),
        p("Glisse l'Omega dans sa pochette avec la fiche de travail et la range au coffre, avec les montres prêtes.", None,
          objets=[mv("obj-omega", "atelier / établi", "atelier / coffre-fort, terminée, prête à expédier")]),
    ])
    j.seg("17:15", "Montres à quartz : bracelets et marche", "atelier", "rt-atelier", "travail", "simple", "assis", [
        p("Démonte les bracelets métalliques de trois montres."),
        p("Les passe à la machine à ultrasons, cycle court.", app=on("machine-ultrasons"), posture="debout"),
        p("Pendant ce temps, contrôle la marche des six montres au chronocomparateur, une par une.", app=on("chronocomparateur")),
        p("Toutes dans les tolérances.", ev=["controle_conforme"], app=off("chronocomparateur")),
        p("Sort les bracelets et les sèche au chiffon.", app=off("machine-ultrasons"), posture="debout"),
        p("Remonte les bracelets."),
        p("Range les six montres dans leur boîte.", "Il reste le polissage léger des boîtes. Vendredi."),
    ])
    j.seg("17:50", "Rangement de l'atelier", "atelier", "rt-atelier", "travail", "simple", "debout", [
        p("Range la Rolex et la boîte des quartz dans le coffre, ferme, remet la clé dans le tiroir.", None,
          objets=[mv("obj-rolex", "atelier / établi", "atelier / coffre-fort"),
                  mv("obj-lot-quartz", "atelier / établi", "atelier / coffre-fort, dans une boîte étiquetée"),
                  mv("obj-cles-coffre", "atelier / serrure du coffre", "atelier / tiroir de l'établi, à droite")]),
        p("Aligne ses outils, éteint la lampe, range ses lunettes.", "La Rolex aussi a un jour d'avance.", ev=["repos_merite", "avance_planning"],
          app=off("lampe-etabli"), objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])

    # ------------------------------------------------------------ soirée
    j.seg("18:00", "Temps libre", "sejour", "rt-soir", "eveille", "repos", "assis", [
        p("S'assoit dans le canapé et allume la radio.", "Le dos fatigue moins, les jours de course.", app=on("radio"), radio=True),
        p("Écoute la radio.", radio=True),
        p("Écoute un reportage sans vraiment le suivre.", radio=True),
        p("Écoute la radio.", "Papa doit regarder les informations régionales.", ev=["pensee_pere"], radio=True),
        p("Éteint la radio et met un disque : les Variations Goldberg.", app=onoff(allume=["lecteur-cd"], eteint=["radio"]), musique=True, posture="debout"),
        p("Écoute, les yeux fermés.", None, ev=["plaisir_simple"], musique=True, posture="allongé"),
        p("Écoute.", musique=True, posture="allongé"),
        p("Écoute la variation la plus lente.", "Gould fredonne en jouant. On l'entend respirer. Ça fait une présence.", musique=True, posture="allongé"),
        p("La nuit tombe : il se lève allumer le séjour, puis se rallonge.", musique=True, posture="allongé"),
        p("Le disque continue.", musique=True, posture="allongé"),
        p("Le disque continue.", musique=True, posture="allongé"),
        p("Arrête le disque.", "Faim.", app=off("lecteur-cd")),
    ])
    j.seg("19:00", "Préparation du dîner", "cuisine", "rt-soir", "eveille", "cuisine", "debout", [
        p("Sort la marmite du réfrigérateur et met la soupe à réchauffer.", None, app=on("plaque-1"),
          objets=[mv("obj-marmite", "cuisine / réfrigérateur", "cuisine / plaque électrique")],
          consommation=[c("soupe_poireaux", 1)]),
        p("Bat deux œufs et fait une omelette.", None, app=on("plaque-2"),
          consommation=[c("oeufs", 2), c("beurre", 10)]),
        p("Sert un bol de soupe et l'omelette, éteint les plaques.", None, app=off("plaque-1", "plaque-2")),
    ])
    j.seg("19:15", "Dîner", "sejour", "rt-soir", "eveille", "repos", "assis", [
        p("Dîne à la table du séjour avec un verre d'eau.", "Deux soirs que la soupe et moi, on se tient compagnie.",
          effets={"faim": 55, "soif": 20}, ev=["repas_seul"]),
        p("Termine son omelette."),
        p("Reste assis un moment, les mains autour du bol vide."),
    ])
    j.seg("19:30", "Vaisselle", "cuisine", "rt-soir", "eveille", "simple", "debout", [
        p("Rapporte la vaisselle."),
        p("Laisse refroidir la soupe."),
        p("Remet la marmite au réfrigérateur : deux portions restantes.", None,
          objets=[mv("obj-marmite", "cuisine / plaque électrique", "cuisine / réfrigérateur")]),
        p("Fait la vaisselle : bol, assiette, poêle."),
        p("Essuie et range."),
        p("Passe aux toilettes.", piece="wc", effets={"toilettes": "vide"}),
    ])
    j.seg("20:00", "Montre du grand-père : les pivots (séance 2)", "atelier", "rt-soir", "loisir", "precision", "assis", [
        p("Allume la lampe d'établi, remet ses lunettes, regarde la photo de René.", "Les pivots, grand-père.",
          ev=["souvenir_grand_pere"], app=on("lampe-etabli"),
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Sort l'ébauche de sa boîte et la remet dans la pince du tour.", ev=["operation_delicate"],
          objets=[mv("obj-acier-axe", "atelier / établi, boîte à côté de la montre de gousset (ébauche d'axe)", "atelier / tour d'horloger")]),
        p("Vérifie le centrage au comparateur et affûte le burin, plus fin qu'hier.", ev=["controle_conforme"]),
        p("Met le tour en marche et attaque le pivot côté balancier.", "Lentement. C'est le métal qui décide de la vitesse.",
          ev=["operation_delicate"], app=on("tour")),
        p("Réduit le diamètre par passes d'un centième.", ev=["operation_delicate"]),
        p("Contrôle au micromètre : 0,14 mm, puis 0,12 après une dernière passe.", "Deux centièmes de réserve pour après la trempe. On s'arrête là.",
          ev=["operation_delicate"]),
        p("Forme la portée conique du pivot.", ev=["operation_delicate"]),
        p("Contrôle sous la loupe : pivot droit, sans bavure.", ev=["geste_reussi"]),
        p("Retourne la pièce dans la pince et la recentre au comparateur.", ev=["operation_delicate"]),
        p("Attaque le second pivot.", ev=["operation_delicate"]),
        p("Réduit par passes d'un centième.", "Les yeux piquent. Encore un pivot.", ev=["operation_delicate"]),
        p("Mesure : 0,13 ? Il remesure : 0,12.", "On mesure trois fois. Toujours. Surtout fatigué.", ev=["mesure_incertaine"]),
        p("Forme la portée conique.", ev=["operation_delicate"]),
        p("Contrôle sous la loupe : droit, propre.", ev=["geste_reussi"]),
        p("Tronçonne l'axe du barreau, d'un seul geste.", "Il est encore mou, mais il existe.", ev=["operation_delicate"]),
        p("Arrête le tour. L'axe tient sur le bout de son doigt.", "Un axe de balancier. Trois millimètres. Six ans d'attente.",
          ev=["beaute_du_geste"], app=off("tour")),
        p("Le range dans sa boîte, sur un lit de papier de soie.", None,
          objets=[mv("obj-acier-axe", "atelier / tour d'horloger", "atelier / établi, boîte à côté de la montre de gousset (axe ébauché, avant trempe)")]),
        p("Sent la fatigue lui tomber dessus. Remet à demain la préparation de la trempe, note les cotes et aligne ses outils.",
          "Les mains deviennent lourdes. On arrête. La trempe se prépare demain, reposé.", charge="simple"),
    ])
    j.seg("21:30", "Rangement", "atelier", "rt-soir", "eveille", "simple", "debout", [
        p("Repose la cloche de verre sur la montre de gousset."),
        p("Éteint la lampe, range ses lunettes.", app=off("lampe-etabli"),
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("21:40", "Chocolat", "cuisine", "rt-soir", "eveille", "repos", "debout", [
        p("Mange deux carrés de chocolat noir et boit un verre d'eau.", "Au lit tôt, ce soir.",
          consommation=[c("chocolat_noir", 2)], effets={"faim": 5, "soif": 20}, ev=["plaisir_simple"]),
    ])
    j.seg("21:45", "Toilette du soir", "salle-de-bain", "rt-soir", "eveille", "simple", "debout", [
        p("Passe aux toilettes.", piece="wc", effets={"toilettes": "vide"}),
        p("Se brosse les dents, se lave le visage.", effets={"hygiene": 10}),
        p("Range sa brosse à dents."),
    ])
    j.seg("22:00", "Coucher", "chambre", "rt-soir", "eveille", "repos", "debout", [
        p("Se déshabille, range ses vêtements et pose sa montre sur la table de chevet.",
          objets=[mv("obj-montre-poignet", "poignet gauche", "chambre / table de chevet")]),
        p("Se couche, prend son carnet et écrit.",
          "« Mardi 9 mars. 7 km. Rolex remontée, ressort neuf, plus 12. Omega validée. Les pivots sont faits. Couché tôt. Demain la trempe, et le match. »",
          ev=["ecriture_carnet"], posture="assis",
          objets=[mv("obj-carnet", "chambre / table de chevet, sous le livre", "dans sa main")]),
        p("Repose le carnet sous le livre et lit deux pages (page 150).", mode="lecture", charge="lecture", posture="allongé",
          objets=[mv("obj-carnet", "dans sa main", "chambre / table de chevet, sous le livre")]),
    ])
    j.seg("22:15", "Endormissement", "chambre", "rt-soir", "eveille", "repos", "allongé", [
        p("Éteint la lumière.", "Demain soir, Madrid. Lyon a gagné l'aller, un à zéro.", app=off("lumiere-chambre")),
        p("Les jambes sont lourdes, agréablement.", "La trempe. Ne pas la rater.", ev=["anticipation_delicate"]),
        p("Glisse dans le sommeil.", charge="sommeil"),
    ])
    fin = [p("Dort.", phase_sommeil="léger") for _ in range(idx("22:30"), idx("22:45"))]
    fin += [p("Dort.", phase_sommeil="profond") for _ in range(idx("22:45"), 288)]
    j.seg("22:30", "Sommeil", "chambre", "sommeil", "sommeil", "sommeil", "allongé", fin)

    j.ecarts = [
        "07:15 : descend la poubelle en partant courir (automatisme : poubelle plus qu'à moitié pleine).",
        "08:55 : passe par la chambre pour régler sa montre sur le réveil avant d'ouvrir l'atelier.",
        "13:55 : rapporte le livre dans la chambre dès la fin de la lecture, après l'oubli de la veille.",
        "Pas de radio au déjeuner ; un disque de Bach en fin de journée.",
        "21:25 : fatigue après la course (énergie sous le seuil d'alerte) ; séance de l'atelier écourtée, préparation de la trempe remise à demain.",
        "22:15 : extinction 45 minutes plus tôt que d'habitude (automatisme aut-fatigue).",
    ]
    j.resume = {
        "travail": {
            "tr-rolex": "démontage, nettoyage, ressort neuf, remontage, échappement et balancier (325 min) ; reste 50 min : réglage fin et emboîtage",
            "tr-omega": "observation de 24 h terminée (+4 s) ; prête à expédier",
            "tr-quartz": "piles, joints, étanchéité, bracelets et contrôle de marche (75 min) ; reste 105 min",
        },
        "objectifs": {
            "ob-montre": "séance 2 sur 4 : les deux pivots ébauchés avec 2 centièmes de réserve, axe tronçonné ; restent la préparation et la trempe, le revenu et le polissage",
            "ob-course": "1re sortie sur 3 : boucle courte de 7 km",
            "ob-lecture": "« La Route » : page 138 → 150",
        },
    }
    j.bilan = [
        "**Course** : boucle courte de 7 km (descente des pentes, quais de Saône, remontée en partie à pied), 132 marches d'escalier.",
        "**Rolex** : remontée avec son ressort neuf ; +12 s/j avant réglage fin ; 50 minutes restantes.",
        "**Omega** : observation validée (+4 s en 24 h), prête à expédier.",
        "**Montres à quartz** : piles, joints, bracelets et contrôle de marche faits ; reste le polissage des boîtes.",
        "**Montre du grand-père** : les deux pivots ébauchés, l'axe tronçonné ; demain la trempe.",
        "**Lecture** : page 138 → 150.",
        "**Fatigue** : énergie sous le seuil d'alerte en fin de soirée ; soirée écourtée et coucher à 22:15.",
    ]
    return j
