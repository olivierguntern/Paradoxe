"""Lundi 8 mars 2010 — contenu rédigé de la journée de Thomas Berthier.

Thomas reste chez lui : atelier (Omega, début de la Rolex), cuisine, lecture,
première séance de tournage de l'axe de la montre de son grand-père.
"""
from moteur import Journee, idx, mv, off, on, onoff, p


def rediger():
    j = Journee("2010-03-08", "lundi", extinction="23:00")
    CYCLES = [
        ("00:00", "00:30", "profond", None, None),
        ("00:30", "00:45", "léger", None, None),
        ("00:45", "01:00", "paradoxal", "Des rouages tournent lentement dans le noir, sans aucun bruit.", None),
        ("01:00", "01:10", "léger", None, None),
        ("01:10", "01:55", "profond", None, None),
        ("01:55", "02:10", "léger", None, None),
        ("02:10", "02:30", "paradoxal", "Il cherche une vis minuscule tombée entre les lames du parquet ; ses doigts sont trop gros pour l'attraper.", None),
        ("02:30", "02:40", "léger", None, None),
        ("02:40", "03:10", "profond", None, None),
        ("03:10", "03:30", "léger", None, None),
        ("03:30", "04:00", "paradoxal", "Il court le long d'un quai qui ne finit pas ; la Saône coule à l'envers.", None),
        ("04:00", "04:05", "micro-éveil", None, None),
        ("04:05", "04:25", "léger", None, None),
        ("04:25", "04:40", "profond", None, None),
        ("04:40", "05:00", "léger", None, None),
        ("05:00", "05:30", "paradoxal", "L'atelier de son grand-père à Besançon. René lui tend une loupe et dit quelque chose qu'il n'entend pas.", "reve_grand_pere"),
        ("05:30", "05:50", "léger", None, None),
        ("05:50", "06:00", "profond", None, None),
        ("06:00", "06:25", "léger", None, None),
        ("06:25", "06:55", "paradoxal", "Le même atelier. Une montre posée sur l'établi tictaque de plus en plus fort.", "reve_grand_pere"),
        ("06:55", "07:00", "léger", None, None),
    ]
    nuit = []
    for d, f, phase, reve, ev in CYCLES:
        for k, i in enumerate(range(idx(d), idx(f))):
            if phase == "micro-éveil":
                nuit.append(p("Se retourne, remonte la couette sur son épaule et se rendort aussitôt.", phase_sommeil=phase))
            else:
                nuit.append(p("Dort.", phase_sommeil=phase, reve=reve, ev=[ev] if (ev and k == 0) else []))
    j.seg("00:00", "Nuit de dimanche à lundi", "chambre", "sommeil", "sommeil", "sommeil", "allongé", nuit)

    j.seg("07:00", "Réveil", "chambre", "rt-matin-simple", "eveille", "repos", "allongé", [
        p("La sonnerie du réveil retentit. Il l'éteint du plat de la main, allume la lampe de chevet et reste allongé.",
          "Encore l'atelier de grand-père. Qu'est-ce qu'il disait ?", ev=["reveil_sonnerie", "souvenir_grand_pere"],
          app=on("lumiere-chambre")),
    ])
    j.seg("07:05", "Toilettes", "wc", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Se lève, passe aux toilettes.", "Lundi. Tout recommence. C'est bien, un lundi.", effets={"toilettes": "vide"}),
    ])
    j.seg("07:10", "Douche et rasage", "salle-de-bain", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Boit un verre d'eau au lavabo, se déshabille et met son tee-shirt de nuit dans le panier à linge.",
          "Le panier est à moitié plein. Mercredi, la machine.", effets={"soif": 20}),
        p("Prend sa douche, l'eau un peu trop chaude.",
          "L'Omega d'abord : nettoyage, remontage, réglage. Six heures, si tout va bien.", effets={"hygiene": 75}, ev=["plaisir_simple"]),
        p("Se rase de près devant le miroir.", "Rasé le lundi et le vendredi. Une semaine propre aux deux bouts."),
    ])
    j.seg("07:25", "S'habille", "chambre", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Enfile une chemise bleue, un pull gris, un jean et ses chaussons en feutre. Attache sa montre LIP à son poignet.",
          "Elle tourne encore. Quarante heures de réserve, elle a tenu la nuit.",
          objets=[mv("obj-montre-poignet", "chambre / table de chevet", "poignet gauche")]),
    ])
    j.seg("07:30", "Petit-déjeuner", "cuisine", "rt-matin-simple", "eveille", "cuisine", "debout", [
        p("Passe par le séjour pour allumer la radio (France Inter), laisse la porte de la cuisine ouverte. Remplit la cafetière italienne et la pose sur la plaque.",
          "Le paquet entamé suffira pour aujourd'hui et demain matin.", via=["sejour"],
          app=on("radio", "plaque-1"),
          objets=[mv("obj-cafetiere", "cuisine / égouttoir", "cuisine / plaque électrique")],
          consommation=[{"produit": "café moulu", "quantite": "1 dose (paquet entamé)"}], radio=True),
        p("Sort deux tranches de pain du congélateur et les fait griller à la poêle pendant que le café monte.",
          "Journée des femmes, dit la radio. Maman doit déjà être debout depuis une heure.", ev=["souvenir_tendre"],
          consommation=[{"produit": "pain de campagne en tranches", "quantite": "2 tranches"}], radio=True),
        p("Éteint la plaque. Beurre ses tartines, met de la confiture d'abricot et se sert un café dans la tasse bleue.",
          None, app=off("plaque-1"), objets=[mv("obj-tasse", "cuisine / égouttoir", "cuisine / plan de travail")],
          consommation=[{"produit": "beurre", "quantite": "10 g"}, {"produit": "confiture d'abricot", "quantite": "2 cuillères (pot entamé)"}],
          effets={"faim": 40, "soif": 15, "cafe": True}, ev=["plaisir_simple"], radio=True),
        p("Mange debout près de la fenêtre en écoutant le journal.",
          "Papa écoute la même radio, à Besançon. Il fait sûrement semblant d'aller bien.", ev=["pensee_pere"], radio=True),
    ])
    j.seg("07:50", "Rangement et montre", "cuisine", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Rince la tasse et la cafetière, les pose sur l'égouttoir. Remonte sa montre : vingt tours de couronne.",
          "Vingt tours, pas un de plus. On ne force jamais un ressort.",
          objets=[mv("obj-tasse", "cuisine / plan de travail", "cuisine / égouttoir"),
                  mv("obj-cafetiere", "cuisine / plaque électrique", "cuisine / égouttoir")], radio=True),
    ])
    j.seg("07:55", "Réglage de la montre", "chambre", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Compare sa montre au réveil radio-piloté : elle avance de quatre secondes. Il tire la couronne et la recale à la seconde.",
          "Quatre secondes en vingt-quatre heures. Elle vieillit bien.", ev=["controle_conforme"], radio=True),
    ])
    doc = [
        p("Prend l'ordinateur portable dans la bibliothèque, s'installe sur le canapé et ouvre la documentation technique du calibre de la Rolex.",
          "La Rolex mercredi et jeudi. Autant savoir où je mets les mains.", app=on("ordinateur"),
          objets=[mv("obj-netbook", "sejour / bibliothèque, étagère du bas", "sejour / table basse")], radio=True),
        p("Lit la procédure de démontage du mécanisme automatique.", "L'inverseur, attention à l'inverseur.", radio=True),
        p("Lit la page sur le barillet et le ressort de remplacement.", "Le ressort neuf est dans le tiroir de l'établi. Arrivé samedi avec les montres.", radio=True),
        p("Note mentalement l'ordre des huiles à utiliser.", "Huile fine pour l'échappement, graisse pour le barillet. Comme toujours.", radio=True),
        p("Regarde les vues éclatées du mouvement.", "Beau calibre. Simple et costaud.", radio=True),
        p("Lit la partie sur le réglage du spiral.", radio=True),
        p("Éteint l'ordinateur et regarde la cour par la fenêtre.", "Le ciel est gris sur les toits d'en face.", app=off("ordinateur"), radio=True),
        p("Range l'ordinateur sur l'étagère du bas de la bibliothèque.",
          objets=[mv("obj-netbook", "sejour / table basse", "sejour / bibliothèque, étagère du bas")], posture="debout", radio=True),
        p("Reste assis quelques minutes à écouter la radio.", "Personne ne m'attend nulle part aujourd'hui. Ça a du bon.", radio=True),
    ]
    j.seg("08:00", "Lecture technique", "sejour", "rt-matin-simple", "eveille", "lecture", "assis", doc)
    j.seg("08:45", "Étirements", "salle-de-bain", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Éteint la radio en quittant le séjour. Fait ses étirements du dos devant le miroir.", "Rien qui tire ce matin.", app=off("radio")),
        p("Termine les étirements, se lave les mains."),
    ])
    j.seg("08:55", "Ouverture de l'atelier", "atelier", "rt-matin-simple", "eveille", "simple", "debout", [
        p("Allume la lampe d'établi, aligne ses outils, prend la clé dans le tiroir et ouvre le coffre-fort. Regarde un instant la photo de son grand-père.",
          "Bonjour, grand-père. On s'y met.", ev=["souvenir_grand_pere"], app=on("lampe-etabli"),
          objets=[mv("obj-cles-coffre", "atelier / tiroir de l'établi, à droite", "atelier / serrure du coffre")]),
    ])

    j.seg("09:00", "Omega : nettoyage et remontage du rouage", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Chausse ses lunettes demi-lunes et examine le plateau de l'Omega démontée.", "Tout est là : platine, ponts, rouage, barillet. Le balancier à part.",
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Dispose les pièces dans les paniers de la machine à ultrasons, le balancier dans le petit panier séparé.", "Le spiral ne doit jamais toucher le reste.", posture="debout"),
        p("Lance le cycle : nettoyage, deux rinçages, séchage. Quarante minutes.", "Quarante minutes. Je m'occupe de la boîte.", app=on("machine-ultrasons"), posture="debout"),
        p("Retire les vieux joints du fond et de la couronne.", "Durcis comme du bois. Ils n'avaient pas été changés depuis longtemps."),
        p("Nettoie la carrure et le fond au pinceau, sans polir.", "On ne polit pas une boîte de 1962. On la nettoie, on la respecte."),
        p("Polit la glace en plexiglas avec un peu de pâte.", "Henri disait : une montre, ça se respecte, même une à quartz.", ev=["souvenir_tendre"]),
        p("Dépoussière le cadran et les aiguilles à la poire soufflante."),
        p("Prépare les joints neufs dans une petite boîte."),
        p("Note l'état de la boîte sur la fiche de travail."),
        p("Surveille la machine en rangeant le pinceau et la pâte.", "Ce soir, le tour. Le premier copeau de l'axe."),
        p("La machine s'arrête. Sort les paniers et laisse sécher les pièces sous une cloche.", app=off("machine-ultrasons"), posture="debout"),
        p("Contrôle à la loupe les pivots du rouage, un par un.", "Propres. Pas de rayure, pas d'usure.", ev=["controle_conforme"]),
        p("Contrôle les dents de la roue d'échappement et les levées de l'ancre.", "Les levées sont belles. Celui qui l'a révisée avant moi savait travailler.", ev=["controle_conforme"]),
        p("Graisse le ressort, referme le barillet et huile son arbre.", ev=["operation_delicate"]),
        p("Pose le barillet sur la platine."),
        p("Monte la roue de centre et la roue moyenne.", ev=["operation_delicate"]),
        p("Monte la roue de seconde et la roue d'échappement, puis le pont de rouage.", "Les pivots entrent seuls dans leurs trous. C'est le moment que je préfère.", ev=["geste_reussi"]),
        p("Souffle doucement sur le rouage : il tourne librement.", "Libre. Parfait.", ev=["controle_conforme"]),
    ])
    j.seg("10:30", "Pause", "wc", "rt-atelier", "eveille", "repos", "debout", [
        p("Pose ses lunettes, passe aux toilettes.", effets={"toilettes": "vide"},
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("10:35", "Pause café", "cuisine", "rt-atelier", "eveille", "repos", "debout", [
        p("Se fait un café et boit un verre d'eau.", "Une heure et demie, et le rouage tourne déjà.", app=onoff(allume=["plaque-1"], eteint=["plaque-1"]),
          consommation=[{"produit": "café moulu", "quantite": "1 dose (paquet entamé)"}],
          effets={"soif": 35, "cafe": True}, ev=["plaisir_simple"]),
        p("Rince la tasse, fait quelques étirements en regardant par la fenêtre.", "Les pigeons sur le toit d'en face. Toujours les mêmes, on dirait."),
    ])
    j.seg("10:45", "Omega : huilage, échappement, balancier", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Remet ses lunettes, huile les pivots du rouage à l'huilier.", "Une goutte, pas plus. Trop d'huile, c'est de la poussière dans six mois.",
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")], ev=["operation_delicate"]),
        p("Termine l'huilage des pivots côté cadran.", ev=["operation_delicate"]),
        p("Pose l'ancre.", ev=["operation_delicate"]),
        p("Pose le pont d'ancre et vérifie les ébats."),
        p("Huile les levées de l'ancre.", ev=["operation_delicate"]),
        p("Pose le balancier-spiral.", "Doucement. Le spiral, c'est un cheveu.", ev=["operation_delicate"]),
        p("Visse le pont de balancier."),
        p("Donne quelques tours de remontoir : le balancier ne part pas encore, il manque l'huile des pierres de balancier."),
        p("Huile les pierres de balancier.", ev=["operation_delicate"]),
        p("Le balancier oscille. Il écoute le tic-tac à la loupe.", "Elle bat. Régulière.", ev=["geste_reussi"]),
        p("Monte la minuterie et le mécanisme de mise à l'heure."),
        p("Contrôle le passage de la mise à l'heure.", "Un petit creux de faim. Le poulet."),
        p("Vérifie l'ensemble une dernière fois avant de s'arrêter."),
    ])
    j.seg("11:50", "Préparation du déjeuner", "cuisine", "écart : préparation anticipée", "eveille", "cuisine", "debout", [
        p("Pose ses lunettes. Allume le four à 200 °C. Dispose les deux cuisses de poulet dans un plat : une pour aujourd'hui, une pour demain.",
          "Quarante-cinq minutes de four. Il fallait y penser avant midi.", ev=["oubli_mineur"], app=on("four"),
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")],
          consommation=[{"produit": "cuisses de poulet", "quantite": 2}]),
        p("Épluche quatre pommes de terre, les coupe en quartiers, ajoute huile, sel et herbes, et enfourne le tout.",
          consommation=[{"produit": "pommes de terre", "quantite": "500 g"},
                        {"produit": "condiments de base (huile, sel, poivre, herbes, moutarde)", "quantite": "une pincée d'herbes, un filet d'huile"}]),
    ])
    j.seg("12:00", "Omega : premier contrôle de marche", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Remet ses lunettes, pose le mouvement sur le chronocomparateur.", app=on("chronocomparateur"),
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Lit le premier résultat : avance de quarante secondes par jour, amplitude correcte.", "Quarante secondes. On réglera après le remontage complet."),
        p("Note les mesures sur la fiche de travail.", app=off("chronocomparateur")),
        p("Range le mouvement dans un boîtier de protection."),
        p("Nettoie ses brucelles et les aligne.", "L'odeur du poulet arrive jusqu'ici.", ev=["plaisir_simple"]),
        p("Éteint la lampe d'établi, pose ses lunettes.", app=off("lampe-etabli"),
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("12:30", "Déjeuner", "sejour", "rt-atelier", "eveille", "repos", "debout", [
        p("Met une assiette et des couverts sur la table du séjour."),
        p("Retourne à la cuisine surveiller le four.", piece="cuisine"),
        p("Éteint le four, sort le plat, sert une cuisse et la moitié des pommes de terre.", piece="cuisine", app=off("four")),
        p("Déjeune seul à la table du séjour, avec un grand verre d'eau.", "Un poulet pour deux jours. Un poulet pour un.",
          effets={"faim": 55, "soif": 20}, ev=["repas_seul", "plaisir_simple"], posture="assis"),
        p("Termine son assiette.", "Sophie aurait mis du thym. Elle mettait du thym partout.", ev=["pensee_sophie"], posture="assis"),
        p("Allume la radio pour le journal de 13 heures, débarrasse.", app=on("radio"), radio=True),
    ])
    j.seg("13:00", "Café et vaisselle", "cuisine", "rt-atelier", "eveille", "cuisine", "debout", [
        p("Laisse refroidir le plat.", radio=True),
        p("Met la cuisse restante et les pommes de terre dans une boîte au réfrigérateur.", "Demain midi, avec du riz.", radio=True),
        p("Se fait un café.", app=onoff(allume=["plaque-1"], eteint=["plaque-1"]), consommation=[{"produit": "café moulu", "quantite": "1 dose (paquet entamé)"}],
          effets={"soif": 15, "cafe": True}, ev=["plaisir_simple"], radio=True),
        p("Lave le plat, l'assiette et les couverts.", radio=True),
        p("Essuie et range, rince la tasse et la cafetière. Passe au séjour éteindre la radio.", via_apres=["sejour"], app=off("radio")),
        p("Passe un coup d'éponge sur le plan de travail."),
    ])
    j.seg("13:30", "Repos", "chambre", "rt-atelier", "eveille", "repos", "debout", [
        p("Va chercher son livre sur la table de chevet.", objets=[mv("obj-livre", "chambre / table de chevet", "dans sa main")]),
    ])
    j.seg("13:35", "Lecture et courte sieste", "sejour", "rt-atelier", "lecture", "lecture", "allongé", [
        p("S'allonge sur le canapé et lit « La Route ».", "Le père et le fils sur la route. Le père parle peu. Comme papa.", ev=["lecture_emouvante", "pensee_pere"]),
        p("Continue sa lecture (page 122)."),
        p("Pose le livre ouvert sur son ventre et s'assoupit.", mode="sieste", charge="sommeil"),
        p("Somnole.", mode="sieste", charge="sommeil"),
        p("Se réveille, referme le livre et le pose sur la table basse.", "Dix minutes. Juste ce qu'il fallait.", mode="eveille", charge="repos",
          ev=["plaisir_simple"], objets=[mv("obj-livre", "dans sa main", "sejour / table basse")]),
    ])
    j.seg("14:00", "Omega : automatique, cadran, réglage", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Rallume la lampe, remet ses lunettes. Démonte le mécanisme automatique déjà nettoyé pour l'huiler.", app=on("lampe-etabli"),
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Huile les roues d'inverseur.", "Les inverseurs, c'est là que les automatiques s'usent.", ev=["operation_delicate"]),
        p("Remonte le pont d'automatique."),
        p("Pose la masse oscillante."),
        p("Fait tourner la masse à la main : le remontage s'entend.", ev=["controle_conforme"]),
        p("Contrôle le remontage automatique."),
        p("Pose le cadran.", ev=["operation_delicate"]),
        p("Chasse l'aiguille des heures et celle des minutes.", ev=["operation_delicate"]),
        p("Pose l'aiguille des secondes.", "La trotteuse, la plus délicate. Ne pas toucher le cadran.", ev=["operation_delicate"]),
        p("Vérifie le parallélisme des aiguilles sur un tour complet.", ev=["controle_conforme"]),
        p("Remet le mouvement sur le chronocomparateur, cadran en haut.", app=on("chronocomparateur")),
        p("Mesure cadran en haut : plus 6 secondes par jour."),
        p("Mesure couronne en bas : plus 9.", "On peut faire mieux."),
        p("Déplace très légèrement la raquette.", ev=["operation_delicate"]),
        p("Nouvelle mesure : plus 3 cadran en haut."),
        p("Mesure couronne en bas : plus 5.", "Plus 3, plus 5. Pour une montre de quarante-huit ans, c'est très bien.", ev=["geste_reussi"]),
        p("Mesure les autres positions pour vérifier l'écart.", app=off("chronocomparateur")),
        p("Note les résultats sur la fiche de travail."),
    ])
    j.seg("15:30", "Pause", "wc", "rt-atelier", "eveille", "repos", "debout", [
        p("Pose ses lunettes, passe aux toilettes.", effets={"toilettes": "vide"},
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("15:35", "Pause", "cuisine", "rt-atelier", "eveille", "repos", "debout", [
        p("Boit un verre d'eau, mange une pomme, étire son dos contre le chambranle.", "Plus de café après seize heures.",
          consommation=[{"produit": "pommes", "quantite": 1}], effets={"soif": 20, "faim": 15}),
    ])
    j.seg("15:40", "Omega : emboîtage et contrôle final", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Remet ses lunettes. Pose le mouvement dans la boîte et serre les vis de fixation.", ev=["operation_delicate"],
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Remet la tige et la couronne."),
        p("Pose les joints neufs du fond et de la couronne."),
        p("Graisse légèrement les joints."),
        p("Ferme le fond à la clé."),
        p("Place la montre dans le contrôleur d'étanchéité.", app=on("controleur-etancheite"), posture="debout"),
        p("Lance le test de pression.", "Si ça fuit, on recommence les joints. Ça ne fuira pas.", posture="debout"),
        p("Lit le résultat : aucune fuite.", "Étanche. Enfin, pour une montre de 1962 : à la pluie, pas à la piscine.", ev=["controle_conforme"],
          app=off("controleur-etancheite"), posture="debout"),
        p("Remet le bracelet d'origine, nettoyé ce matin."),
        p("Fait tourner la montre dans sa main pour vérifier le remontage automatique."),
        p("La met à l'heure d'après sa propre montre."),
        p("Remplit la fiche de travail : opérations, mesures, joints changés.", charge="simple"),
        p("Nettoie l'établi.", charge="simple"),
        p("Vide et rince les bacs de la machine à ultrasons.", charge="simple", posture="debout"),
        p("Range les huiles et les joints restants.", charge="simple", posture="debout"),
        p("Essuie la montre avec une peau de chamois.", charge="simple"),
        p("Pose l'Omega cadran en haut sur un coussin pour vingt-quatre heures d'observation.", "Terminée. Un jour d'avance sur le planning.",
          ev=["tache_terminee", "avance_planning"], charge="simple"),
    ])
    j.seg("17:05", "Rolex : premier examen et début du démontage", "atelier", "rt-atelier", "travail", "precision", "assis", [
        p("Sort la Rolex du coffre et l'examine sous la lampe.", "Quelques rayures sur la lunette. Le client les veut, ce sont ses rayures.",
          objets=[mv("obj-rolex", "atelier / coffre-fort", "atelier / établi")]),
        p("Remplit la fiche d'état initial : boîte, verre, couronne, marche.", charge="simple"),
        p("Ouvre le fond avec la clé adaptée."),
        p("Observe le mouvement à la loupe.", "Propre, mais les huiles sont sèches. Le ressort est fatigué, comme prévu."),
        p("Vérifie dans le tiroir de l'établi le ressort de barillet neuf, dans son sachet.", "Il est là. Bien.", ev=["controle_conforme"]),
        p("Démonte la masse oscillante."),
        p("Sort le mouvement de la boîte.", ev=["operation_delicate"]),
        p("Retire les aiguilles avec un protège-cadran.", ev=["operation_delicate"]),
        p("Retire le cadran et range les pièces dans un plateau compartimenté."),
    ])
    j.seg("17:50", "Rangement de l'atelier", "atelier", "rt-atelier", "travail", "simple", "debout", [
        p("Range la Rolex démontée dans son plateau et l'Omega en observation dans le coffre-fort, cadran en haut.",
          objets=[mv("obj-rolex", "atelier / établi", "atelier / coffre-fort"),
                  mv("obj-omega", "atelier / établi, démontée dans un plateau", "atelier / coffre-fort, remontée, en observation")]),
        p("Ferme le coffre, remet la clé dans le tiroir de l'établi, aligne ses outils, éteint la lampe et range ses lunettes.",
          "Journée pleine. Rien n'a résisté.", ev=["repos_merite"], app=off("lampe-etabli"),
          objets=[mv("obj-cles-coffre", "atelier / serrure du coffre", "atelier / tiroir de l'établi, à droite"),
                  mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("18:00", "Temps libre", "sejour", "rt-soir", "eveille", "repos", "assis", [
        p("S'assoit sur le canapé et allume la radio.", "La journée est faite. Le reste est à moi.", app=on("radio"), radio=True),
        p("Écoute la radio, les jambes allongées.", radio=True),
        p("Regarde la lumière baisser sur les toits par la fenêtre.", "Mars. Les jours rallongent, enfin.", ev=["jours_rallongent"], radio=True),
        p("Ferme les yeux quelques minutes, sans dormir.", radio=True),
    ])
    j.seg("18:20", "Préparation de la soupe", "cuisine", "écart : préparation anticipée", "eveille", "cuisine", "debout", [
        p("Sort la marmite en fonte du placard. Épluche trois poireaux.",
          objets=[mv("obj-marmite", "cuisine / placard sous les plaques", "cuisine / plaque électrique")],
          consommation=[{"produit": "poireaux", "quantite": 3}], radio=True),
        p("Épluche les pommes de terre.", consommation=[{"produit": "pommes de terre", "quantite": "500 g"}], radio=True),
        p("Coupe les légumes et un oignon.", "Une soupe pour quatre soirs. Maman faisait pareil.", ev=["souvenir_tendre"],
          consommation=[{"produit": "oignons", "quantite": 1}], radio=True),
        p("Allume la plaque et fait suer les poireaux et l'oignon dans un peu de beurre.", app=on("plaque-1"),
          consommation=[{"produit": "beurre", "quantite": "20 g"}], radio=True),
        p("Ajoute l'eau, les pommes de terre et le sel. Couvre, laisse cuire trente minutes.", radio=True),
    ])
    j.seg("18:45", "Lecture pendant la cuisson", "sejour", "rt-soir", "lecture", "lecture", "allongé", [
        p("Éteint la radio, reprend son livre sur la table basse.", app=off("radio"), posture="assis"),
        p("Lit sur le canapé.", "Le père protège le fils de tout. Même de ce qu'il pense.", ev=["lecture_emouvante", "pensee_pere"]),
        p("Lit (page 130)."),
        p("Pose le livre sur la table basse.", posture="assis"),
    ])
    j.seg("19:05", "Fin de la soupe", "cuisine", "rt-soir", "eveille", "cuisine", "debout", [
        p("Vérifie la cuisson à la pointe du couteau."),
        p("Éteint la plaque, mixe la soupe au mixeur plongeant.", app=onoff(allume=["mixeur"], eteint=["plaque-1", "mixeur"])),
        p("Sert un bol, coupe un morceau de comté et une tranche de pain.",
          consommation=[{"produit": "comté", "quantite": "50 g"}, {"produit": "pain de campagne en tranches", "quantite": "1 tranche"}]),
    ])
    j.seg("19:20", "Dîner", "sejour", "rt-soir", "eveille", "repos", "assis", [
        p("Dîne à la table du séjour, avec un verre d'eau.", "Bonne soupe. Il manque quelqu'un pour le dire.",
          effets={"faim": 55, "soif": 20}, ev=["plaisir_simple", "repas_seul"]),
        p("Termine le comté."),
    ])
    j.seg("19:30", "Vaisselle", "cuisine", "rt-soir", "eveille", "simple", "debout", [
        p("Rapporte le bol à la cuisine."),
        p("Laisse refroidir la soupe."),
        p("Range la marmite avec les trois portions restantes au réfrigérateur.",
          objets=[mv("obj-marmite", "cuisine / plaque électrique", "cuisine / réfrigérateur")]),
        p("Fait la vaisselle : bol, couteau, mixeur."),
        p("Essuie la vaisselle et la range.", "Pas un mot adressé à quelqu'un de toute la journée. Je n'y avais pas pensé.", ev=["constat_isolement"]),
        p("Passe aux toilettes.", piece="wc", effets={"toilettes": "vide"}),
    ])
    j.seg("20:00", "Montre du grand-père : tournage de l'axe (séance 1)", "atelier", "rt-soir", "loisir", "precision", "assis", [
        p("Allume la lampe d'établi, remet ses lunettes, soulève la cloche de verre. Regarde la photo de René.", "À nous deux.",
          ev=["souvenir_grand_pere"], app=on("lampe-etabli"),
          objets=[mv("obj-lunettes", "atelier / établi, dans leur étui", "sur son nez")]),
        p("Prend l'ancien axe cassé dans le plateau de la montre de gousset et mesure sa hauteur totale au micromètre."),
        p("Mesure les diamètres des portées et des pivots.", "Pivot : 0,09 ? Non, 0,10. On mesure trois fois.", ev=["mesure_incertaine"]),
        p("Reporte toutes les cotes sur une feuille."),
        p("Sort le barreau d'acier du tiroir.", objets=[mv("obj-acier-axe", "atelier / tiroir de l'établi", "atelier / tour d'horloger")]),
        p("Serre le barreau dans la pince du tour et le centre.", ev=["operation_delicate"]),
        p("Affûte le burin sur la pierre.", "Un burin mal affûté, c'est un axe raté."),
        p("Met le tour en marche et dégrossit le barreau au burin.", app=on("tour")),
        p("Continue le dégrossissage."),
        p("Contrôle le diamètre au micromètre.", ev=["controle_conforme"]),
        p("Commence la portée du balancier.", ev=["operation_delicate"]),
        p("Travaille la portée du balancier.", "Le copeau sort en spirale bleue. C'est beau.", ev=["beaute_du_geste", "operation_delicate"]),
        p("Termine la portée du balancier.", ev=["operation_delicate"]),
        p("Contrôle la cote : dans la tolérance.", ev=["controle_conforme"]),
        p("Commence la portée du plateau.", ev=["operation_delicate"]),
        p("Travaille la portée du plateau.", ev=["operation_delicate"]),
        p("Termine la portée du plateau et arrête le tour.", ev=["operation_delicate"], app=off("tour")),
        p("Contrôle les cotes. Il reste les pivots, trop délicats pour être commencés si tard.",
          "Pas de pivot à moins de trente minutes de la fin. C'est la règle.", ev=["controle_conforme"]),
        p("Note les cotes atteintes sur la feuille.", charge="simple"),
        p("Regarde l'ébauche sous la loupe.", "Un quart du chemin.", charge="simple"),
        p("Balaie les copeaux du tour.", charge="simple"),
        p("Repense à son grand-père qui tournait ses axes à l'œil.", "Grand-père tournait ses axes sans micromètre. Je n'en suis pas là.",
          ev=["souvenir_grand_pere"], charge="simple"),
        p("Sort l'ébauche de la pince et la range dans une petite boîte.", charge="simple",
          objets=[mv("obj-acier-axe", "atelier / tour d'horloger", "atelier / établi, boîte à côté de la montre de gousset (ébauche d'axe)")]),
        p("Aligne ses outils.", charge="simple"),
    ])
    j.seg("22:00", "Rangement", "atelier", "rt-soir", "eveille", "simple", "debout", [
        p("Repose la cloche de verre sur la montre de gousset."),
        p("Éteint la lampe, range ses lunettes.", app=off("lampe-etabli"),
          objets=[mv("obj-lunettes", "sur son nez", "atelier / établi, dans leur étui")]),
    ])
    j.seg("22:10", "Chocolat", "cuisine", "rt-soir", "eveille", "repos", "debout", [
        p("Mange deux carrés de chocolat noir et boit un verre d'eau.", consommation=[{"produit": "chocolat noir", "quantite": "2 carrés"}],
          effets={"faim": 5, "soif": 20}, ev=["plaisir_simple"]),
    ])
    j.seg("22:15", "Toilette du soir", "salle-de-bain", "rt-soir", "eveille", "simple", "debout", [
        p("Passe aux toilettes.", piece="wc", effets={"toilettes": "vide"}),
        p("Se brosse les dents, se lave le visage.", effets={"hygiene": 10}),
        p("Range sa brosse à dents."),
    ])
    j.seg("22:30", "Coucher", "chambre", "rt-soir", "eveille", "repos", "debout", [
        p("Se déshabille, range ses vêtements dans l'armoire, met un tee-shirt et pose sa montre sur la table de chevet.",
          objets=[mv("obj-montre-poignet", "poignet gauche", "chambre / table de chevet")]),
        p("S'aperçoit que son livre est resté sur la table basse et va le chercher au séjour.", "Le livre. Toujours là où je ne suis pas.",
          ev=["oubli_mineur"], via=["sejour"], objets=[mv("obj-livre", "sejour / table basse", "chambre / table de chevet")]),
        p("Se couche et lit (page 134).", mode="lecture", charge="lecture", posture="allongé"),
        p("Prend son carnet noir et écrit.",
          "« Lundi 8 mars. Omega terminée, plus 3 plus 5. Premier quart de l'axe. Rien d'autre. C'est bien, une journée où il n'y a rien d'autre. »",
          ev=["ecriture_carnet"], posture="assis",
          objets=[mv("obj-carnet", "chambre / table de chevet, sous le livre", "dans sa main")]),
        p("Referme le carnet et le repose sous le livre. Relit quelques pages.", mode="lecture", charge="lecture", posture="allongé",
          objets=[mv("obj-carnet", "dans sa main", "chambre / table de chevet, sous le livre")]),
        p("Lit encore (page 138).", mode="lecture", charge="lecture", posture="allongé"),
    ])
    j.seg("23:00", "Endormissement", "chambre", "rt-soir", "eveille", "repos", "allongé", [
        p("Éteint la lumière.", "Demain, la course. Le réveil est bien sur sept heures.", app=off("lumiere-chambre")),
        p("Écoute le silence de l'immeuble.", "Le tour, demain soir : les pivots.", ev=["anticipation_delicate"]),
        p("Ses pensées ralentissent.", charge="sommeil"),
    ])
    fin = [p("Dort.", phase_sommeil="léger") for _ in range(idx("23:15"), idx("23:30"))]
    fin += [p("Dort.", phase_sommeil="profond") for _ in range(idx("23:30"), 288)]
    j.seg("23:15", "Sommeil", "chambre", "sommeil", "sommeil", "sommeil", "allongé", fin)

    j.ecarts = [
        "11:50-12:00 : mise au four du poulet avant le déjeuner (45 min de cuisson), pris sur le temps de travail.",
        "18:20-18:45 : préparation de la soupe pendant le temps libre (cuisson de 30 min).",
        "19:20 : dîner plus tardif que la routine (19:00) à cause de la cuisson.",
        "22:35 : aller-retour au séjour pour chercher le livre oublié sur la table basse.",
    ]
    j.resume = {
        "travail": {"tr-omega": "terminée à 17:05 (360 min), en observation 24 h ; marche +3 à +5 s/j",
                    "tr-rolex": "examen et démontage commencés (45 min) ; reste 375 min"},
        "objectifs": {"ob-montre": "séance 1 sur 4 : portées du balancier et du plateau tournées ; restent les pivots",
                      "ob-lecture": "« La Route » : page 112 → 138"},
    }
    j.bilan = [
        "**Omega** : terminée à 17:05, en observation 24 h ; marche de +3 à +5 secondes par jour.",
        "**Rolex** : examinée et démontée en partie ; 375 minutes restantes.",
        "**Montre du grand-père** : première séance de tournage de l'axe ; restent les pivots.",
        "**Lecture** : page 112 → 138.",
        "**Escaliers** : aucun, Thomas ne sort pas le lundi.",
    ]
    return j
