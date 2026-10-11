"""Mercredi 10 mars 2010 — contenu rédigé de la journée de Thomas Berthier.

Fin de la Rolex, réparation de la sonnerie de la pendule, polissage des
montres à quartz, lessive, trempe et revenu de l'axe de la montre de son
grand-père, puis Real Madrid – Lyon (1-1) regardé seul à la télévision.
"""
from moteur import Journee, c, idx, mv, off, on, onoff, p


def rediger():
    j = Journee("2010-03-10", "mercredi", extinction="23:10", endormissement=45)

    # ------------------------------------------------------------ nuit
    # Endormi à 22:30 la veille : cycles de 90 minutes à partir de 22:30.
    CYCLES = [
        ("00:00", "00:10", "léger", None, None),
        ("00:10", "00:50", "profond", None, None),
        ("00:50", "01:10", "léger", None, None),
        ("01:10", "01:30", "paradoxal", "Un stade immense et vide ; une seule lampe d'établi éclaire la pelouse.", None),
        ("01:30", "01:40", "léger", None, None),
        ("01:40", "02:10", "profond", None, None),
        ("02:10", "02:30", "léger", None, None),
        ("02:30", "03:00", "paradoxal", "Il plonge une pièce rougie dans l'huile ; la fumée monte et dessine un visage.", None),
        ("03:00", "03:20", "léger", None, None),
        ("03:20", "03:35", "profond", None, None),
        ("03:35", "04:00", "léger", None, None),
        ("04:00", "04:30", "paradoxal", "Grand-père regarde la couleur de l'acier et dit : « Pas encore. »", "reve_grand_pere"),
        ("04:30", "04:35", "micro-éveil", None, None),
        ("04:35", "05:00", "léger", None, None),
        ("05:00", "05:10", "profond", None, None),
        ("05:10", "05:30", "léger", None, None),
        ("05:30", "06:00", "paradoxal", "Sophie dans le séjour cherche ses clés ; il ne sait pas lui dire où elles sont.", "reve_inquiet"),
        ("06:00", "06:30", "léger", None, None),
        ("06:30", "06:50", "paradoxal", "Les quais de Saône sous la neige ; il court sans laisser de traces.", None),
        ("06:50", "06:55", "léger", None, None),
    ]
    nuit = []
    for d, f, phase, reve, ev in CYCLES:
        for k, _ in enumerate(range(idx(d), idx(f))):
            if phase == "micro-éveil":
                nuit.append(p("Se retourne, remonte la couette et se rendort.", phase_sommeil=phase))
            else:
                nuit.append(p("Dort.", phase_sommeil=phase, reve=reve, ev=[ev] if (ev and k == 0) else []))
    j.seg("00:00", "Nuit de mardi à mercredi", "chambre", "sommeil", "sommeil", "sommeil", "allongé", nuit)

    # ------------------------------------------------------------ matin
    j.seg("06:55", "Éveil avant la sonnerie", "chambre", "rt-matin-simple", "eveille", "repos", "allongé", [
        p("Se réveille seul, avant la sonnerie. Reste allongé dans la pénombre.", "Plus de huit heures de sommeil. Les jambes ont récupéré.",
          ev=["plaisir_simple"]),
    ])
    j.seg("07:00", "Lever", "chambre", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Coupe le réveil avant qu'il ne sonne et se lève.", "Mercredi. La trempe ce soir. Et le match.", ev=["anticipation_plaisir"]),
    ])
    j.seg("07:05", "Toilettes", "wc", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Passe aux toilettes.", effets={"toilettes": "vide"}),
    ])
    j.seg("07:10", "Douche", "salle-de-bain", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Boit un verre d'eau au lavabo, se déshabille.", None, effets={"soif": 20}),
        p("Prend sa douche.", "Pas de rasage le mercredi.", effets={"hygiene": 75}, ev=["plaisir_simple"]),
        p("Se sèche, se coiffe.", None),
    ])
    j.seg("07:25", "S'habille", "chambre", "rt-matin-simple", "eveille", "simple", "debout", [
        p("S'habille et attache sa montre.", None, objets=[mv("obj-montre-poignet", "chambre / table de chevet", "poignet gauche")]),
    ])
    j.seg("07:30", "Petit-déjeuner", "cuisine", "rt-matin-simple", "eveille", "cuisine", "debout", [
        p("Passe par le séjour allumer la radio. Prépare le café.", None, via=["sejour"], app=on("radio", "plaque-1"),
          objets=[mv("obj-cafetiere", "cuisine / égouttoir", "cuisine / plaque électrique")], consommation=[c("cafe_moulu", 7)], radio=True),
        p("Fait griller deux tranches de pain.", "La radio parle déjà du match de ce soir.", ev=["anticipation_plaisir"],
          consommation=[c("pain_tranches", 2)], radio=True),
        p("Éteint la plaque, beurre ses tartines, se sert un café dans la tasse bleue.", None, app=off("plaque-1"),
          objets=[mv("obj-tasse", "cuisine / égouttoir", "cuisine / plan de travail")],
          consommation=[c("beurre", 10), c("confiture_abricot", 2)], effets={"faim": 40, "soif": 15, "cafe": True}, ev=["plaisir_simple"], radio=True),
        p("Mange près de la fenêtre.", None, radio=True),
    ])
    j.seg("07:50", "Rangement et montre", "cuisine", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Rince la tasse et la cafetière. Remonte sa montre.", None, radio=True,
          objets=[mv("obj-tasse", "cuisine / plan de travail", "cuisine / égouttoir"),
                  mv("obj-cafetiere", "cuisine / plaque électrique", "cuisine / égouttoir")]),
    ])
    j.seg("07:55", "Réglage de la montre", "chambre", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Règle sa montre sur le réveil : deux secondes d'avance.", "Deux secondes. Elle se stabilise.", ev=["controle_conforme"], radio=True),
    ])
    j.seg("08:00", "Lecture technique : la trempe", "sejour", "rt-matin-simple", "eveille", "lecture", "assis", [
        p("Sort de la bibliothèque son vieux manuel d'horlogerie du lycée et cherche le chapitre sur la trempe.", "Morteau, 1997. Les pages sont encore tachées d'huile.",
          radio=True, ev=["souvenir_tendre"]),
        p("Relit la température de trempe : rouge cerise, environ 800 degrés.", None, radio=True),
        p("Relit le revenu : le bleu, autour de 300 degrés.", "Le bleu. Grand-père disait « bleu de roi ».", ev=["souvenir_grand_pere"], radio=True),
        p("Relit la protection au savon contre l'oxydation.", None, radio=True),
        p("Note les étapes sur une fiche.", "Savon, rouge cerise, huile, lime, pierre, plaque de laiton, bleu.", radio=True),
        p("Écoute la radio, le manuel sur les genoux.", None, radio=True),
        p("Range le manuel dans la bibliothèque.", None, posture="debout", radio=True),
        p("Regarde la cour.", "Le ciel est bas.", radio=True),
        p("Reste assis à écouter la radio.", None, radio=True),
    ])
    j.seg("08:45", "Étirements", "salle-de-bain", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Éteint la radio en quittant le séjour, fait ses étirements.", None, app=off("radio")),
        p("Termine ses étirements, se lave les mains.", None),
    ])
    j.seg("08:55", "Ouverture de l'atelier", "atelier", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Allume la lampe d'établi, aligne ses outils, ouvre le coffre. Regarde la photo de son grand-père.", "La Rolex d'abord.",
          ev=["souvenir_grand_pere"], app=on("lampe-etabli"),
          objets=[mv("obj-cles-coffre", "atelier / tiroir de l'établi, à droite", "atelier / serrure du coffre")]),
    ])

    # ------------------------------------------------------------ matinée
    j.seg("09:00", "Rolex : réglage fin et emboîtage", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Chausse ses lunettes, sort la Rolex et pose le mouvement sur le chronocomparateur.", "Les huiles ont reposé.",
          app=on("chronocomparateur"),
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez"), mv("obj-rolex", "atelier / coffre-fort", "atelier / établi")]),
        p("Relevé : plus 10 secondes par jour cadran en haut, plus 13 couronne en bas.", None),
        p("Déplace l'index de réglage d'un cheveu.", None, ev=["operation_delicate"]),
        p("Nouveau relevé : plus 2, plus 4.", "Plus 2, plus 4. Une Rolex de trente-cinq ans.", ev=["geste_reussi"], app=off("chronocomparateur")),
        p("Pose le cadran et les aiguilles, contrôle le passage de la date à minuit.", None, ev=["operation_delicate"]),
        p("Emboîte le mouvement et remonte la masse oscillante.", None, ev=["operation_delicate"]),
        p("Change les joints du fond et de la couronne, ferme le fond.", None),
        p("Teste l'étanchéité : elle tient la pression.", None, app=onoff(allume=["controleur-etancheite"], eteint=["controleur-etancheite"]),
          ev=["controle_conforme"]),
        p("Remplit la fiche de travail.", None, charge="simple"),
        p("Range la Rolex au coffre, cadran en haut, pour vingt-quatre heures d'observation.", "Terminée. Mercredi au lieu de jeudi.",
          ev=["tache_terminee", "avance_planning"], charge="simple",
          objets=[mv("obj-rolex", "atelier / établi", "atelier / coffre-fort, terminée, en observation")]),
    ])
    j.seg("09:50", "Pendule : démontage", "atelier", "rt-atelier", "travail", "simple", "debout", [
        p("Descend la pendule de l'étagère et la pose sur un tapis de protection.", "Huit kilos de marbre noir. Fin du dix-neuvième.",
          objets=[mv("obj-pendule", "atelier / étagère de fournitures, étage du bas", "atelier / établi")]),
        p("Ouvre la porte arrière, décroche le balancier.", None),
        p("Laisse descendre les ressorts des deux barillets avec la clé de remontage.", None, ev=["operation_delicate"]),
        p("Dévisse les pieds du mouvement et le sort de la caisse avec le cadran.", None, ev=["operation_delicate"]),
        p("Fait sonner la pendule à la main : douze coups au lieu de trois.", "Elle compte comme elle veut.", posture="assis", charge="precision"),
        p("Examine la roue de compte et son loquet à la loupe : le bout du loquet est usé.", "Voilà le coupable.", posture="assis", charge="precision"),
        p("Retire le cadran et les aiguilles.", None, posture="assis", charge="precision"),
        p("Démonte la cadrature côté cadran.", None, posture="assis", charge="precision"),
    ])
    j.seg("10:30", "Pause", "wc", "rt-atelier", "eveille", "repos", "debout", [
        p("Pose ses lunettes, passe aux toilettes.", effets={"toilettes": "vide"},
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("10:35", "Pause café", "cuisine", "rt-atelier", "eveille", "repos", "debout", [
        p("Se fait un café.", None, app=onoff(allume=["plaque-1"], eteint=["plaque-1"]), consommation=[c("cafe_moulu", 7)],
          effets={"soif": 15, "cafe": True}, ev=["plaisir_simple"]),
        p("Boit un verre d'eau, s'étire.", "Le marbre, ça se porte avec le dos.", effets={"soif": 20}),
    ])
    j.seg("10:45", "Pendule : démontage complet, nettoyage, réparations", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Remet ses lunettes. Sépare les platines : rouage de mouvement d'un côté, rouage de sonnerie de l'autre.", None, ev=["operation_delicate"],
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Sort les deux barillets.", None),
        p("Démonte les mobiles du rouage de sonnerie.", None),
        p("Démonte le rouage de mouvement.", None),
        p("Ouvre les barillets et nettoie les ressorts.", None, ev=["operation_delicate"]),
        p("Met les petites pièces dans le grand panier de la machine à ultrasons et la lance.", None, app=on("machine-ultrasons"), posture="debout"),
        p("Lave les platines au pinceau.", None, charge="simple"),
        p("Sèche les platines.", None, charge="simple"),
        p("Polit les pivots usés au brunissoir.", None, ev=["operation_delicate"]),
        p("Contrôle les trous des platines : un trou ovalisé côté sonnerie.", "Ovalisé. Il faut un bouchon."),
        p("Alèse le trou ovalisé.", None, ev=["operation_delicate"]),
        p("Ajuste un bouchon en laiton et le chasse dans la platine.", None, ev=["operation_delicate"]),
        p("La machine s'arrête. Alèse le bouchon au diamètre du pivot.", None, ev=["operation_delicate"], app=off("machine-ultrasons")),
        p("Contrôle l'ébat du pivot dans son nouveau trou : juste ce qu'il faut.", None, ev=["geste_reussi"]),
        p("Sort les petites pièces de la machine et les sèche.", None, posture="debout"),
        p("Contrôle les dents de la roue de compte.", None, ev=["controle_conforme"]),
        p("Reprend le bout du loquet usé à la lime fine.", "Un dixième, pas plus. Sinon il ne retiendra plus rien.", ev=["operation_delicate"]),
        p("Polit le loquet à la pierre.", None),
        p("Essaie le loquet sur la roue de compte, à la main : il accroche net.", None, ev=["geste_reussi"]),
        p("Range les pièces propres sous une cloche.", None),
        p("Éteint la lampe, pose ses lunettes.", "Le plus gros est fait. Cet après-midi, le remontage.", app=off("lampe-etabli"),
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])

    # ------------------------------------------------------------ midi
    j.seg("12:30", "Déjeuner", "cuisine", "rt-atelier", "eveille", "cuisine", "debout", [
        p("Met l'eau des pâtes à bouillir.", None, app=on("plaque-1")),
        p("Verse les pâtes, ouvre une boîte de thon.", None, consommation=[c("pates", 125), c("thon", 1)]),
        p("Égoutte les pâtes, les mélange au thon avec un filet d'huile et du poivre, éteint la plaque.", None,
          app=off("plaque-1"), consommation=[c("condiments", 1)]),
        p("Déjeune à la table du séjour avec un verre d'eau.", "Pâtes au thon. Le repas des étudiants. Et des horlogers seuls.",
          piece="sejour", posture="assis", charge="repos", effets={"faim": 55, "soif": 20}, ev=["repas_seul"]),
        p("Termine son assiette.", "Un à zéro à l'aller, Makoun. Il faut tenir ce soir.", piece="sejour", posture="assis", charge="repos",
          ev=["anticipation_plaisir"]),
        p("Débarrasse.", None, piece="sejour", charge="repos"),
    ])
    j.seg("13:00", "Café et vaisselle", "cuisine", "rt-atelier", "eveille", "cuisine", "debout", [
        p("Se fait un café.", app=onoff(allume=["plaque-1"], eteint=["plaque-1"]), consommation=[c("cafe_moulu", 7)],
          effets={"soif": 15, "cafe": True}, ev=["plaisir_simple"]),
        p("Lave la casserole et l'assiette."),
        p("Essuie et range."),
        p("Rince la tasse et la cafetière."),
        p("Boit un verre d'eau.", effets={"soif": 20}),
        p("Regarde la cour par la fenêtre.", "Le même gris qu'hier."),
    ])
    j.seg("13:30", "Repos", "chambre", "rt-atelier", "eveille", "repos", "debout", [
        p("Va chercher son livre.", objets=[mv("obj-livre", "chambre / table de chevet", "dans sa main")]),
    ])
    j.seg("13:35", "Lecture", "sejour", "rt-atelier", "lecture", "lecture", "allongé", [
        p("Lit sur le canapé.", "Le père tousse. Ça ne présage rien de bon.", ev=["lecture_emouvante", "pensee_pere"]),
        p("Lit (page 155)."),
        p("Lit (page 160)."),
        p("Ferme les yeux quelques minutes.", mode="sieste", charge="sommeil"),
    ])
    j.seg("13:55", "Rangement du livre", "chambre", "rt-atelier", "eveille", "repos", "debout", [
        p("Rapporte le livre sur la table de chevet.", None, objets=[mv("obj-livre", "dans sa main", "chambre / table de chevet")]),
    ])

    # ------------------------------------------------------------ après-midi
    j.seg("14:00", "Pendule : remontage", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Rallume la lampe, remet ses lunettes. Huile les ressorts et referme les barillets.", None, ev=["operation_delicate"], app=on("lampe-etabli"),
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Pose les mobiles du rouage de mouvement sur la platine arrière.", None),
        p("Pose les mobiles du rouage de sonnerie.", None),
        p("Présente la platine avant et guide les pivots un à un.", "Douze pivots à faire entrer en même temps. C'est là qu'on apprend la patience.",
          ev=["operation_delicate"]),
        p("Continue de guider les pivots.", None, ev=["operation_delicate"]),
        p("Les pivots entrent. Il goupille les platines.", None, ev=["geste_reussi"]),
        p("Vérifie la liberté des deux rouages.", None, ev=["controle_conforme"]),
        p("Huile les pivots du rouage de mouvement.", None, ev=["operation_delicate"]),
        p("Huile les pivots du rouage de sonnerie.", None, ev=["operation_delicate"]),
        p("Pose l'ancre et son pont, huile les levées.", None, ev=["operation_delicate"]),
        p("Remonte la cadrature.", None),
        p("Pose la roue de compte et son loquet repris.", None),
        p("Règle l'avertissement : la sonnerie doit se préparer juste avant l'heure.", "Ni trop tôt, ni trop tard. Papa dirait : comme un train.",
          ev=["operation_delicate", "pensee_pere"]),
        p("Accroche le mouvement sur un support d'essai, remonte un peu les deux ressorts.", None),
        p("Accroche le balancier et le lance : la pendule bat.", None, ev=["geste_reussi"]),
        p("Écoute le battement : il boite légèrement.", "Elle boite. Il faut la remettre d'échappement."),
        p("Tord délicatement la fourchette pour égaliser le battement.", None, ev=["operation_delicate"]),
        p("Le battement est égal.", "Tic, tac. Égal.", ev=["controle_conforme"]),
    ])
    j.seg("15:30", "Pause", "wc", "rt-atelier", "eveille", "repos", "debout", [
        p("Pose ses lunettes, passe aux toilettes.", effets={"toilettes": "vide"},
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("15:35", "Pause", "cuisine", "rt-atelier", "eveille", "repos", "debout", [
        p("Boit un verre d'eau et mange une pomme.", None, consommation=[c("pommes", 1)], effets={"soif": 20, "faim": 15}),
    ])
    j.seg("15:40", "Pendule : sonnerie, emboîtage", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Remet ses lunettes. Fait tourner les aiguilles pour déclencher la sonnerie : un coup à la demie.", None,
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Continue jusqu'à l'heure suivante : quatre coups au lieu de trois.", "Le compte est décalé d'une heure. Rien n'est encore synchronisé."),
        p("Soulève le loquet et fait tourner la roue de compte pour la caler sur les aiguilles.", None, ev=["operation_delicate"]),
        p("Nouvel essai : trois coups pour trois heures.", None, ev=["geste_reussi"]),
        p("Fait passer les heures une à une jusqu'à midi : le compte est juste à chaque fois.", "Douze coups. Elle sait compter à nouveau.",
          ev=["controle_conforme"]),
        p("Remet le cadran et les aiguilles, à l'heure de sa montre.", None),
        p("Replace le mouvement dans la caisse en marbre et serre les pieds.", None, ev=["operation_delicate"], posture="debout"),
        p("Raccroche le balancier.", None),
        p("Met la pendule d'aplomb sur l'établi.", None),
        p("Remonte les deux ressorts à fond.", None),
        p("Referme la porte arrière.", None),
        p("Remplit la fiche : nettoyage, bouchon, loquet repris, sonnerie recalée.", None, charge="simple"),
        p("Repose la pendule sur l'étagère, en marche, pour l'observation.", "Deux jours d'avance sur la pendule.",
          ev=["tache_terminee", "avance_planning"], posture="debout", charge="simple",
          objets=[mv("obj-pendule", "atelier / établi", "atelier / étagère de fournitures, étage du bas, réparée, en observation")]),
    ])
    j.seg("16:45", "Montres à quartz : polissage des boîtes", "atelier", "rt-atelier", "travail", "simple", "assis", [
        p("Sort la boîte des montres à quartz du coffre.", None,
          objets=[mv("obj-lot-quartz", "atelier / coffre-fort, dans une boîte étiquetée", "atelier / établi")]),
        p("Polit à la pâte la boîte de la première montre.", None),
        p("Polit la deuxième.", None),
        p("La pendule sonne cinq coups, au même instant que sa montre.", "Cinq coups. À l'heure.", ev=["geste_reussi"]),
        p("Polit la troisième, la montre de dame plaquée or, sans appuyer.", "Le plaqué or, on le caresse. On ne le frotte pas."),
        p("Polit la quatrième.", None),
        p("Polit la cinquième.", None),
        p("Nettoie les traces de pâte au chiffon.", None),
        p("Polit la sixième.", None),
        p("La pendule sonne un coup pour la demie.", None, ev=["controle_conforme"]),
        p("Contrôle les six boîtes sous la lampe.", None),
        p("Range les six montres dans leur boîte.", "Il reste les fiches et les factures. Vendredi."),
        p("Nettoie l'établi.", None),
    ])
    j.seg("17:50", "Rangement de l'atelier", "atelier", "rt-atelier", "travail", "simple", "debout", [
        p("Range la boîte des quartz au coffre, ferme, remet la clé dans le tiroir. Met la sonnerie de la pendule sur silence pour la nuit.", None,
          objets=[mv("obj-lot-quartz", "atelier / établi", "atelier / coffre-fort, dans une boîte étiquetée"),
                  mv("obj-cles-coffre", "atelier / serrure du coffre", "atelier / tiroir de l'établi, à droite")]),
        p("Aligne ses outils, éteint la lampe, range ses lunettes.", "Rolex, pendule. Une bonne journée.", ev=["repos_merite"],
          app=off("lampe-etabli"), objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])

    # ------------------------------------------------------------ soirée : lessive et trempe
    j.seg("18:00", "Lessive", "salle-de-bain", "rt-mercredi-soir", "eveille", "simple", "debout", [
        p("Va chercher le panier à linge dans la salle de bain.", None,
          objets=[mv("obj-panier-linge", "salle-de-bain / sol", "dans ses bras")]),
        p("Trie le linge sur le carrelage de la cuisine et remplit la machine.", None, piece="cuisine",
          objets=[mv("obj-panier-linge", "dans ses bras", "cuisine / sol, devant la machine"),
                  mv("obj-tenue-course", "salle-de-bain / panier à linge", "cuisine / machine à laver")]),
        p("Verse une dose de lessive et lance un cycle de 90 minutes à 40 degrés.", "Une heure et demie. La trempe pendant ce temps.",
          piece="cuisine", app=on("machine-a-laver"), consommation=[c("lessive", 1)]),
    ])
    j.seg("18:15", "Montre du grand-père : trempe et revenu (séance 3)", "atelier", "rt-mercredi-soir", "loisir", "precision", "assis", [
        p("Allume la lampe d'établi, remet ses lunettes, regarde la photo de René.", "Ce soir, l'acier devient un axe.",
          ev=["souvenir_grand_pere"], app=on("lampe-etabli"), objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Ouvre la fenêtre de l'atelier en grand.", "L'huile de trempe fume. L'air doit circuler.", posture="debout"),
        p("Prépare la lampe à alcool, le pot d'huile, une pince fine et une plaque de laiton.", "Ce que je n'ai pas fait hier soir. Reposé, c'est mieux."),
        p("Enrobe l'axe de savon contre l'oxydation et le saisit dans la pince.", None, ev=["operation_delicate"],
          objets=[mv("obj-acier-axe", "atelier / établi, boîte à côté de la montre de gousset (axe ébauché, avant trempe)", "dans la pince de trempe")]),
        p("Allume la lampe à alcool.", None, app=on("lampe-alcool"), ev=["operation_delicate"]),
        p("Chauffe l'axe dans la flamme. Il passe au rouge sombre.", "Pas encore. Rouge cerise.", ev=["operation_delicate"]),
        p("Rouge cerise. Il le plonge d'un coup dans l'huile.", "Maintenant.", ev=["operation_delicate"]),
        p("Sort l'axe de l'huile, l'essuie. Teste à la lime : elle glisse sans mordre.", "Trempé. Dur comme du verre. Et aussi cassant.", ev=["geste_reussi"]),
        p("Blanchit une face de l'axe à la pierre pour voir monter les couleurs.", None, ev=["operation_delicate"]),
        p("Pose l'axe sur la plaque de laiton au-dessus de la flamme.", None, ev=["operation_delicate"]),
        p("Regarde la couleur monter : paille, puis brun.", "Paille. Brun. Pas encore.", ev=["beaute_du_geste"]),
        p("Pourpre, puis bleu. Il retire la plaque du feu.", "Bleu. Exactement le bleu de grand-père.", ev=["geste_reussi", "souvenir_grand_pere"]),
        p("Éteint la lampe à alcool et laisse refroidir l'axe sur la plaque.", None, app=off("lampe-alcool"),
          objets=[mv("obj-acier-axe", "dans la pince de trempe", "atelier / établi, sur la plaque de laiton")]),
        p("Nettoie l'axe à l'essence et l'examine à la loupe : aucune fissure.", None, ev=["controle_conforme"]),
        p("Ferme la fenêtre.", "Huile chaude et alcool brûlé. L'odeur de l'atelier de Besançon.", ev=["souvenir_grand_pere"], posture="debout"),
        p("Range l'axe dans sa boîte : trempé et revenu.", "Restent le polissage des pivots et le montage. Samedi.",
          objets=[mv("obj-acier-axe", "atelier / établi, sur la plaque de laiton", "atelier / établi, boîte à côté de la montre de gousset (axe trempé et revenu)")]),
        p("Range la lampe à alcool et le pot d'huile.", None, charge="simple"),
        p("Éteint la lampe d'établi, range ses lunettes.", None, app=off("lampe-etabli"), charge="simple",
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("19:45", "Étendage", "cuisine", "rt-mercredi-soir", "eveille", "simple", "debout", [
        p("La machine s'arrête. Il sort le linge et le met dans le panier.", None, app=off("machine-a-laver"),
          objets=[mv("obj-panier-linge", "cuisine / sol, devant la machine", "dans ses bras"),
                  mv("obj-tenue-course", "cuisine / machine à laver", "panier à linge, mouillée")]),
        p("Déplie l'étendoir près du radiateur de la chambre.", None, piece="chambre",
          objets=[mv("obj-etendoir", "chambre / replié derrière la porte", "chambre / déplié près du radiateur"),
                  mv("obj-panier-linge", "dans ses bras", "chambre / sol")]),
        p("Étend les chemises et les tee-shirts.", None, piece="chambre"),
        p("Étend la tenue de course et les chaussettes.", "Elle sera sèche pour demain matin. Juste.", piece="chambre",
          objets=[mv("obj-tenue-course", "panier à linge, mouillée", "chambre / étendoir")]),
        p("Étend le reste.", "Un étendoir plein, c'est une semaine qui se voit.", piece="chambre"),
        p("Rapporte le panier vide dans la salle de bain.", None, piece="salle-de-bain",
          objets=[mv("obj-panier-linge", "chambre / sol", "salle-de-bain / sol")]),
    ])
    j.seg("20:15", "Dîner de match", "cuisine", "rt-mercredi-soir", "eveille", "cuisine", "debout", [
        p("Sort un steak haché du congélateur.", "Le match dans une demi-heure.", ev=["anticipation_plaisir"], consommation=[c("steaks_haches", 1)]),
        p("Met l'eau des pâtes à bouillir.", None, app=on("plaque-1")),
        p("Verse les pâtes, met le steak à cuire à la poêle.", None, app=on("plaque-2"), consommation=[c("pates", 125)]),
        p("Retourne le steak.", None),
        p("Égoutte les pâtes, sert l'assiette, éteint les plaques.", None, app=off("plaque-1", "plaque-2"), consommation=[c("condiments", 1)]),
        p("Sort une bière du réfrigérateur et la décapsule.", "Une bière les soirs de match. Pas deux.", consommation=[c("biere", 1)]),
    ])

    # ------------------------------------------------------------ Real Madrid – Lyon
    M = dict(tele="match")
    j.seg("20:45", "Real Madrid – Lyon : première mi-temps", "sejour", "rt-mercredi-soir", "loisir", "lecture", "assis", [
        p("Allume la télévision, s'installe sur le canapé avec son assiette. Coup d'envoi au stade Santiago-Bernabéu.",
          "Un à zéro à l'aller. Il faut tenir.", app=on("television"), ev=["match_tension"], **M),
        p("Cristiano Ronaldo ouvre le score pour le Real dès la sixième minute. Thomas mange sans quitter l'écran.", "Déjà. Six minutes.",
          ev=["but_adverse"], effets={"faim": 55, "soif": 20}, **M),
        p("Le Real presse, Lyon recule.", "Ils vont en prendre un deuxième.", ev=["match_tension"], **M),
        p("Pose son assiette vide sur la table basse.", "Julien doit hurler devant sa télé.", ev=["match_tension", "pensee_ami"], **M),
        p("Lyon subit. Il ne quitte pas l'écran.", None, ev=["match_tension"], **M),
        p("Le gardien lyonnais sauve encore.", "Lloris. Heureusement qu'il est là.", ev=["match_tension"], **M),
        p("Boit une gorgée de bière.", "Un partout sur les deux matchs. Si ça reste comme ça, prolongation.", ev=["match_tension"], **M),
        p("Le Real domine toujours.", "Envie pressante. J'attendrai la mi-temps.", ev=["match_tension"], **M),
        p("Fin de la première mi-temps qui approche.", None, ev=["match_tension"], **M),
    ])
    j.seg("21:30", "Mi-temps", "cuisine", "rt-mercredi-soir", "eveille", "repos", "debout", [
        p("Mi-temps. Rapporte l'assiette à la cuisine.", None, **M),
        p("Passe aux toilettes.", None, piece="wc", effets={"toilettes": "vide"}),
        p("Se rassoit sur le canapé.", "Papa doit regarder aussi. Il est pour Sochaux, mais ce soir il est lyonnais.",
          piece="sejour", posture="assis", ev=["pensee_pere"], **M),
    ])
    j.seg("21:45", "Real Madrid – Lyon : seconde mi-temps", "sejour", "rt-mercredi-soir", "loisir", "lecture", "assis", [
        p("Reprise. Le Real attaque d'emblée.", None, ev=["match_tension"], **M),
        p("Les occasions s'enchaînent devant le but lyonnais.", None, ev=["match_tension"], **M),
        p("Lyon ressort un peu.", "Ils respirent.", ev=["match_tension"], **M),
        p("Se penche en avant, les coudes sur les genoux.", None, ev=["match_tension"], **M),
        p("Le match se tend.", None, ev=["match_tension"], **M),
        p("Lyon pousse enfin.", None, ev=["match_tension"], **M),
        p("Miralem Pjanić égalise à la 75e minute. Thomas se lève d'un bond.", "Pjanić ! Un partout !", ev=["but_equipe"], posture="debout", **M),
        p("Se rassoit. Le Real doit maintenant marquer deux fois.", "Ils doivent en mettre deux. Tenir. Juste tenir.", ev=["match_tension"], **M),
        p("Les dernières minutes défilent.", None, ev=["match_tension"], **M),
        p("Arrêts de jeu. Il ne respire plus.", None, ev=["match_tension"], **M),
    ])
    j.seg("22:35", "Qualification", "sejour", "rt-mercredi-soir", "eveille", "repos", "debout", [
        p("Coup de sifflet final : 1-1. Lyon est qualifié pour les quarts de finale. Il éteint la télévision.",
          "Qualifiés, au Bernabéu. Julien doit être dans la rue.", app=off("television"), ev=["qualification_equipe", "pensee_ami"], **M),
    ])
    j.seg("22:40", "Avant de se coucher", "cuisine", "rt-mercredi-soir", "eveille", "simple", "debout", [
        p("Rapporte la bouteille vide, rince le verre.", "Je l'ai vu seul, et c'était quand même beau."),
        p("Passe aux toilettes.", None, piece="wc", effets={"toilettes": "vide"}),
        p("Se brosse les dents.", None, piece="salle-de-bain", effets={"hygiene": 10}),
        p("Se lave le visage, range sa brosse à dents.", None, piece="salle-de-bain"),
    ])
    j.seg("23:00", "Coucher", "chambre", "rt-mercredi-soir", "eveille", "repos", "debout", [
        p("Se déshabille et pose sa montre sur la table de chevet.", None,
          objets=[mv("obj-montre-poignet", "poignet gauche", "chambre / table de chevet")]),
        p("Se couche, écrit dans son carnet et le repose sous le livre.",
          "« Mercredi 10 mars. Rolex terminée. Pendule terminée, elle sait compter. Axe trempé, revenu bleu. Real 1, Lyon 1 : qualifiés. »",
          ev=["ecriture_carnet"], posture="assis",
          objets=[mv("obj-carnet", "chambre / table de chevet, sous le livre", "dans sa main"),
                  mv("obj-carnet", "dans sa main", "chambre / table de chevet, sous le livre")]),
    ])
    j.seg("23:10", "Endormissement difficile", "chambre", "rt-mercredi-soir", "eveille", "repos", "allongé", [
        p("Éteint la lumière.", "Le but de Pjanić. Je le revois.", app=off("lumiere-chambre"), ev=["souvenir_excitant"]),
        p("Repasse le match dans sa tête.", None, ev=["souvenir_excitant"]),
        p("Se retourne.", "Le bleu de l'acier. Exactement le bleu."),
        p("Garde les yeux ouverts dans le noir.", "Il faut dormir. Demain, la course."),
        p("Compte les coups d'une pendule imaginaire.", "Un, deux, trois... Elle sait compter, elle."),
        p("Ses pensées ralentissent.", None),
        p("Somnole par moments.", None),
        p("Ses pensées se défont.", None),
        p("S'endort.", None, charge="sommeil"),
    ])
    j.seg("23:55", "Sommeil", "chambre", "sommeil", "sommeil", "sommeil", "allongé", [
        p("Dort.", phase_sommeil="léger"),
    ])

    j.ecarts = [
        "06:55 : réveil naturel avant la sonnerie, après plus de huit heures de sommeil.",
        "Pas de rasage : il se rase le lundi et le vendredi les jours sans course.",
        "18:15 : prépare la trempe qu'il avait remise la veille par fatigue.",
        "21:15-21:30 : attend la mi-temps pour aller aux toilettes (besoin sous le seuil d'alerte, anxiété en hausse).",
        "23:10 : endormissement en 45 minutes, l'excitation du match dépassant le seuil.",
    ]
    j.resume = {
        "travail": {
            "tr-rolex": "réglage fin (+2/+4 s/j), emboîtage, étanchéité ; terminée, en observation 24 h",
            "tr-pendule": "démontage, nettoyage, bouchon, loquet repris, sonnerie recalée ; terminée (300 min), en observation",
            "tr-quartz": "polissage des six boîtes (65 min) ; reste 40 min",
        },
        "objectifs": {
            "ob-montre": "séance 3 sur 4 : trempe et revenu bleu de l'axe ; restent le polissage des pivots et le montage",
            "ob-maison": "lessive faite et linge étendu",
            "ob-lecture": "« La Route » : page 150 → 160",
        },
    }
    j.bilan = [
        "**Rolex** : terminée (+2 à +4 s/j), en observation jusqu'à jeudi.",
        "**Pendule** : sonnerie réparée et recalée, deux jours d'avance.",
        "**Montres à quartz** : boîtes polies ; restent les fiches et factures.",
        "**Montre du grand-père** : axe trempé puis revenu au bleu.",
        "**Lessive** : faite, linge étendu dans la chambre.",
        "**Match** : Real Madrid 1 – 1 Lyon (Ronaldo, puis Pjanić à la 75e) ; Lyon qualifié. Regardé seul ; excitation au plus haut, endormissement en 45 minutes.",
    ]
    return j
