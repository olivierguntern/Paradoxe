"""Construit data/agents/robert-chazal/blocs.json, les scènes de l'agent de Robert Chazal.

Les scènes du lundi au mercredi sont extraites des journées de référence
(outils/journees/robert-chazal/), rejouées en mémoire depuis la fiche ; les
scènes de jeudi à dimanche (variantes du jour, belote, fin de semaine, vote,
randonnée…) sont rédigées ici.

Usage : python3 outils/construire_scenes_robert.py
"""
import copy
import importlib.util
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "outils"))
sys.path.insert(0, os.path.join(RACINE, "outils", "journees", "robert-chazal"))
import moteur  # noqa: E402

FICHE = json.load(open(os.path.join(RACINE, "data", "personnages", "robert-chazal.json"), encoding="utf-8"))


def segments_de_reference():
    """Segments rédigés des trois journées de référence, chacune partant de la fin de la précédente."""
    out, etat = {}, moteur.etat_initial_depuis_fiche(FICHE)
    for d in ("08", "09", "10"):
        date = f"2010-03-{d}"
        if d != "08":
            etat = json.load(open(os.path.join(RACINE, "data", "references", "robert-chazal", f"2010-03-{int(d) - 1:02d}.json"), encoding="utf-8"))["etat_final"]
        spec = importlib.util.spec_from_file_location("j" + d, os.path.join(RACINE, "outils", "journees", "robert-chazal", f"{date}.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        out[date] = m.rediger(etat).segments
    return out


S = segments_de_reference()
GARDE = ("action", "pensee", "piece", "lieu", "mode", "charge", "posture", "via", "via_apres", "sortie", "retour", "effets", "ev", "app",
         "radio", "tele", "musique", "parcours", "nouveaux_objets", "argent")
MENUS = FICHE["menus_prevus"]

def conv(seg, st):
    out = {"titre": seg["titre"], "routine": seg["routine"]}
    for k in ("piece", "lieu", "mode", "charge", "posture"):
        out[k] = seg[k]
    for k in GARDE:
        if k in st and st[k] not in (None, [], {}):
            out[k] = copy.deepcopy(st[k])
    if st.get("objets"):
        out["objets"] = [[o["objet"], o["vers"]] for o in st["objets"]]
    if st.get("consommation"):
        c = [[x["produit"], x["quantite"]] for x in st["consommation"]]
        trouve = None
        if c == MENUS["petit_dejeuner"]["ingredients"]:
            trouve = "petit_dejeuner"
        for j, m in MENUS.items():
            if isinstance(m, dict) and "dejeuner" in m:
                for mom in ("dejeuner", "diner"):
                    if c == m[mom]["ingredients"]:
                        trouve = mom
        if trouve:
            out["repas"] = trouve
        else:
            out["consommation"] = c
    if out.get("pensee") is None:
        out.pop("pensee", None)
    return out

def seg(date, debut):
    for s in S[date]:
        if s["debut"] == debut:
            return [conv(s, st) for st in s["pas"]]
    raise KeyError((date, debut))

def segs(date, debuts):
    out = []
    for d in debuts:
        out += seg(date, d)
    return out

MA, ME, LU = "2010-03-09", "2010-03-10", "2010-03-08"
B = {}
B["reveil"] = {"defaut": seg(MA, "05:30"), "mercredi": seg(ME, "05:30")}
B["toilette"] = {"defaut": seg(MA, "05:35"), "mercredi": seg(ME, "05:35")}
B["petit_dejeuner"] = {"defaut": seg(MA, "05:55"), "mercredi": seg(ME, "05:55")}
B["depart_matin"] = {"defaut": seg(MA, "06:10"), "mercredi": seg(ME, "06:10")}
B["arrivee_boutique"] = {"defaut": seg(MA, "06:30"), "mercredi": seg(ME, "06:30")}
B["pain"] = {"defaut": seg(MA, "06:35"), "mercredi": seg(ME, "06:35")}
B["grossiste"] = {"defaut": seg(MA, "06:40")}
B["mise_en_rayon"] = {"defaut": seg(ME, "06:40")}
B["ouverture"] = {"defaut": seg(MA, "06:55"), "mercredi": seg(ME, "06:55")}
B["fermeture_midi"] = {"defaut": seg(MA, "12:00"), "mercredi": seg(ME, "12:00")}
B["dejeuner"] = {"defaut": seg(MA, "12:25"), "mercredi": seg(ME, "12:25")}
B["sieste"] = {"defaut": seg(MA, "13:10"), "mercredi": seg(ME, "13:10")}
B["depart_apres_midi"] = {"defaut": seg(MA, "13:25"), "mercredi": seg(ME, "13:25")}
B["reouverture"] = {"defaut": seg(MA, "13:45"), "mercredi": seg(ME, "13:45")}
B["fermeture_soir"] = {"defaut": seg(MA, "19:00"), "mercredi": seg(ME, "19:00")}
B["soiree"] = {"defaut": seg(MA, "19:35")}
B["tele"] = {"defaut": seg(MA, "20:30")}
B["toilette_soir"] = {"defaut": seg(MA, "21:45")}
B["soiree_match"] = {"defaut": segs(ME, ["19:35", "19:50", "20:30"])}
B["apres_match"] = {"defaut": seg(ME, "22:40")}
B["toilette_soir_match"] = {"defaut": seg(ME, "22:45")}
B["lundi"] = {"defaut": segs(LU, ["07:15", "07:20", "07:40", "07:55", "08:45"])}
B["lundi_banque"] = {"defaut": segs(LU, ["09:10", "09:15", "09:30"])}
B["lundi_matinee"] = {"defaut": segs(LU, ["09:55"])}
B["lundi_apres_midi"] = {"defaut": segs(LU, ["12:10", "13:05", "13:15", "14:15", "16:30", "17:30", "18:45", "19:30"])}
B["lundi_cinema"] = {"defaut": segs(LU, ["20:05", "20:15", "22:40"])}
B["lundi_coucher"] = {"defaut": seg(LU, "23:00")}
# trajets : textes seulement (la découpe vient des règles)
def textes(date, debut):
    return [st["action"] for st in seg(date, debut)], [st.get("pensee") for st in seg(date, debut)], [st.get("ev", []) for st in seg(date, debut)]
R = {}
for nom, date, debut in (("aube", MA, "06:15"), ("midi", MA, "12:10"), ("apres_midi", MA, "13:30"), ("soir", MA, "19:15"),
                         ("lundi_matin", LU, "08:50"), ("lundi_midi", LU, "09:35"), ("cinema_aller", LU, "19:50"), ("cinema_retour", LU, "22:45")):
    t, pe, ev = textes(date, debut)
    R[nom] = {"defaut": {"textes": t, "pensees": pe, "ev": ev}}
for nom, debut in (("aube", "06:15"), ("midi", "12:10"), ("apres_midi", "13:30"), ("soir", "19:15")):
    t, pe, ev = textes(ME, debut)
    R[nom]["mercredi"] = {"textes": t, "pensees": pe, "ev": ev}
B["routes"] = R
for k, v in B.items():
    if k != "routes":
        print(k, {kk: len(vv) for kk, vv in v.items()})

# ------------------------------------------------------------------ rôles, journaux et modèles de texte
def remplacer(obj, a, b):
    if isinstance(obj, str):
        return obj.replace(a, b)
    if isinstance(obj, list):
        return [remplacer(x, a, b) for x in obj]
    if isinstance(obj, dict):
        return {k: remplacer(v, a, b) for k, v in obj.items()}
    return obj

for nom in list(B):
    if nom == "routes":
        continue
    for var in list(B[nom]):
        L = B[nom][var]
        if nom.startswith("lundi"):
            L = remplacer(L, "obj-progres-0308", "JOURNAL")
        elif var == "mercredi" or nom in ("soiree_match", "apres_match", "mise_en_rayon"):
            L = remplacer(remplacer(L, "obj-progres-0309", "JOURNAL_VEILLE"), "obj-progres-0310", "JOURNAL")
        else:
            L = remplacer(remplacer(L, "obj-progres-0308", "JOURNAL_VEILLE"), "obj-progres-0309", "JOURNAL")
        for st in L:
            st.pop("nouveaux_objets", None) if any(o.get("id") == "JOURNAL" for o in st.get("nouveaux_objets", [])) else None
        B[nom][var] = L

def role(nom, i, r, var=None, **kw):
    for v, L in B[nom].items():
        if var and v != var:
            continue
        L[i]["role"] = r
        L[i].update(kw)

role("depart_matin", 0, "depart_maison")
role("depart_apres_midi", 0, "depart_maison")
role("arrivee_boutique", 0, "arrivee_boutique")
role("reouverture", 0, "arrivee_boutique")
role("pain", 0, "pain", modele="Allume la boutique, lève le rideau à mi-hauteur. Le livreur de la boulangerie pose les panières : {pain}, et Le Progrès sur le dessus{reprise}. Robert met de côté {mis_de_cote} pour la maison.")
role("grossiste", 0, "grossiste", modele_pensee="{n_commande} lignes. Le chauffeur dit que le lait augmente en avril.")
role("fermeture_midi", 1, "caisse_midi", modele="Dans l'arrière-boutique, compte la caisse du matin : {especes} en espèces au-delà du fond, qu'il range dans la sacoche du coffre. Rince la tasse de Lucas.",
     modele_pensee="{recette} ce matin, cartes comprises.")
role("fermeture_soir", 1, "caisse_soir", modele="Compte la caisse au bureau : {especes} en espèces depuis midi, qu'il range dans la sacoche du coffre. La caisse tombe juste. La journée fait {recette_jour}.")
role("fermeture_soir", 2, "cabas_soir", modele="Remplit {contenant} pour Josiane : {liste}. Glisse Le Progrès dessus, éteint la boutique.",
     modele_vide="Rien à rapporter ce soir pour la maison : Josiane a tout ce qu'il faut. Prend Le Progrès sous le bras, éteint la boutique.",
     modele_pensee="{liste_courte}. Tout y est.")
role("dejeuner", 0, "arrivee_maison")
role("dejeuner", 4, "demande_josiane", var="defaut")
role("dejeuner", 3, "demande_josiane", var="mercredi")
role("soiree", 0, "arrivee_soir")
role("soiree_match", 0, "arrivee_soir")
for st in B["dejeuner"].values():
    for x in st:
        if x.get("role") == "demande_josiane":
            x["modele"] = "Josiane : « Ce soir, {plat_soir}. Rapporte {liste}. »"
            x["modele_rien"] = "Josiane : « Ce soir, {plat_soir}. J'ai tout ce qu'il faut. »"
            x["modele_pensee"] = "{liste_courte}. {liste_courte}."
# lundi : jour de congé, seulement la banque
LB = B["lundi_banque"]["defaut"]
LB[0]["role"] = "banque_recette"
LB[0]["modele"] = ("Gare la Kangoo à sa place dans la cour et entre par la porte de derrière, sans allumer la boutique : le rideau reste baissé. Dans "
                   "l'arrière-boutique, ouvre le coffre, recompte la recette de la semaine passée, {coffre}, et la glisse dans une pochette de dépôt "
                   "de la banque avec le bordereau rempli.")
LB[2]["role"] = "depot"
LA = B["lundi_apres_midi"]["defaut"]
LA[0]["role"] = "journal_josiane"

# ------------------------------------------------------------------ scènes rédigées pour l'agent (jeudi à dimanche)
def pas_comme(modele, **kw):
    st = copy.deepcopy(modele)
    st.pop("pensee", None)
    st.update(kw)
    return st

def variante(nom, var, textes, pensees=None, base="defaut"):
    L = copy.deepcopy(B[nom][base])
    for k, t in enumerate(textes):
        L[k]["action"] = t
        L[k].pop("pensee", None)
        if pensees and k < len(pensees) and pensees[k]:
            L[k]["pensee"] = pensees[k]
    B[nom][var] = L

variante("reveil", "jeudi", ["Le réveil sonne. Il le cherche à tâtons, l'arrête, reste assis au bord du lit, la tête lourde. Attache sa Seiko, prend ses lunettes."],
         ["Cinq heures quarante-cinq de sommeil. Pjanić, va. Ça valait le coup."])
variante("reveil", "vendredi", ["Le réveil sonne. Il l'arrête, s'assoit au bord du lit, attache sa Seiko et prend ses lunettes."], ["Vendredi. Le grossiste, et le week-end."])
variante("reveil", "samedi", ["Le réveil sonne. Josiane grogne ; il l'arrête vite, s'assoit, attache sa Seiko et prend ses lunettes."], ["Samedi. La belote, ce soir."])
variante("reveil", "dimanche", ["Le réveil sonne. Il l'arrête, s'assoit dans le noir, attache sa Seiko et prend ses lunettes."], ["Dimanche. Ce matin la boutique, cet après-midi les monts d'Or."])
variante("toilette", "jeudi", ["Passe aux toilettes de la salle de bain.", "Douche longue, pour se réveiller.", "Se rase, en se coupant un peu sous le menton.", "S'habille avec les vêtements préparés sur le tabouret."])
variante("toilette", "dimanche", ["Passe aux toilettes de la salle de bain.", "Douche.", "Se rase et taille sa moustache aux ciseaux, comme chaque dimanche.", "S'habille avec les vêtements préparés sur le tabouret."])
variante("petit_dejeuner", "jeudi", ["Descend à la cuisine, met la cafetière en route et la radio tout bas, beurre deux tartines.",
         "Mange debout contre le buffet. À la radio, on ne parle que de Lyon et de Pjanić.", "Rince son bol, laisse le café au chaud pour Josiane, éteint la radio et la cafetière."],
         [None, "Il a fallu que je l'entende trois fois pour y croire.", None], base="mercredi")
variante("petit_dejeuner", "dimanche", ["Descend à la cuisine, met la cafetière en route et la radio tout bas, beurre deux tartines.",
         "Mange debout contre le buffet ; la radio parle des élections régionales d'aujourd'hui.", "Rince son bol, éteint la radio et la cafetière."],
         [None, "Voter, cet après-midi. Et la randonnée, si le dos veut bien.", None], base="mercredi")
variante("pain", "samedi", ["(modèle)"]); B["pain"]["samedi"][0]["pensee"] = "Quatre-vingts baguettes le samedi. Il en restera pas."
variante("pain", "dimanche", ["(modèle)"]); B["pain"]["dimanche"][0]["pensee"] = "Deux baguettes de côté : une pour aujourd'hui, une pour demain."
variante("mise_en_rayon", "jeudi", ["Remplit l'étal de fruits depuis la réserve.", "Range les yaourts et le lait dans la vitrine réfrigérée, les dates courtes devant.",
         "Lit la une du Progrès, appuyé au comptoir : « L'OL au bout du suspense. »"], [None, None, "Ils l'ont mis en grand. Pjanić en photo, les bras en l'air."])
variante("mise_en_rayon", "samedi", ["Remplit l'étal de fruits depuis la réserve : le samedi, il en faut deux fois plus.", "Range les yaourts et le lait dans la vitrine réfrigérée.",
         "Feuillette Le Progrès : les programmes du week-end, le tiercé."])
variante("mise_en_rayon", "dimanche", ["Remplit l'étal de fruits depuis la réserve.", "Range les produits frais, les dates courtes devant.",
         "Feuillette Le Progrès du dimanche : le premier tour des régionales, les bureaux de vote ouverts jusqu'à 18 heures."])
variante("ouverture", "samedi", ["Lève le rideau de fer, allume la radio et la caisse, compte le fond de caisse. Le samedi, ça commence tôt."])
variante("ouverture", "dimanche", ["Lève le rideau de fer, allume la radio et la caisse. Le dimanche matin, la Grande-Rue est vide jusqu'à huit heures."])
for v in ("jeudi", "vendredi", "samedi"):
    variante("dejeuner", v, {
        "jeudi": ["Entre par le garage, accroche sa veste, pose ses clés et son portefeuille. Josiane réchauffe le reste de poulet.",
                  "Se lave les mains, boit un verre d'eau, s'assoit.", "Mangent le reste de poulet basquaise et le riz.",
                  "Josiane lui trouve une petite mine. Il raconte le but de Pjanić, debout dans le salon, à minuit moins le quart.", "(modèle)",
                  "Une pomme en dessert.", "Se fait un café, plus serré que d'habitude.", "Passe aux toilettes du rez-de-chaussée.", "S'installe dans son fauteuil."],
        "vendredi": ["Entre par le garage, accroche sa veste, pose ses clés et son portefeuille. Ça sent le poisson.",
                     "Se lave les mains, boit un verre d'eau, s'assoit.", "Mangent le colin et les pommes vapeur.",
                     "Josiane raconte le cabinet : une patiente a apporté des bugnes pour tout le monde.", "(modèle)",
                     "Un fruit en dessert.", "Se fait un café et le boit debout à la fenêtre.", "Passe aux toilettes du rez-de-chaussée.", "S'installe dans son fauteuil."],
        "samedi": ["Entre par le garage, accroche sa veste, pose ses clés et son portefeuille. Josiane a passé la matinée au marché de Cusset.",
                   "Se lave les mains, boit un verre d'eau, s'assoit.", "Mangent les steaks hachés et les haricots verts.",
                   "Josiane a croisé Monique Morel au marché : la belote tient toujours pour ce soir.", "(modèle)",
                   "Un fruit en dessert.", "Se fait un café.", "Passe aux toilettes du rez-de-chaussée.", "S'installe dans son fauteuil."],
    }[v], {"jeudi": [None, None, "Le poulet, il est encore meilleur le lendemain.", "Elle dit que je suis fou. Elle a pas tort.", None, None, None, None, None],
           "vendredi": [None, None, None, None, None, None, None, None, None],
           "samedi": [None, None, None, "Gérard va encore annoncer belote avec un roi sec.", None, None, None, None, None]}[v])
    B["dejeuner"][v][4]["action"] = "(modèle)"
for v, t in (("jeudi", "Josiane lui trouve une petite mine. Il raconte le but de Pjanić, debout dans le salon, à minuit moins le quart."),):
    pass
for v, textes_soir in (("jeudi", ["Entre par le garage, pose ce qu'il rapporte sur la table de la cuisine, accroche sa veste.",
                                  "Raconte sa journée à Josiane : Ahmed et son 1-1, la commande du grossiste.", "Se lave les mains, boit un grand verre d'eau, s'assoit.",
                                  "Dîner : {plat}.", "Le comté ; Josiane parle des régionales de dimanche.", "Il bâille à s'en décrocher la mâchoire. Josiane rit.",
                                  "Débarrasse ; essuie la vaisselle.", "Range la vaisselle.", "Passe aux toilettes du rez-de-chaussée.",
                                  "Prend Le Progrès et s'installe dans son fauteuil.", "Allume la télévision."]),
                       ("vendredi", ["Entre par le garage, pose ce qu'il rapporte sur la table de la cuisine, accroche sa veste.",
                                     "Raconte sa journée à Josiane : les étudiantes ont réglé leur ardoise, le grossiste était à l'heure.",
                                     "Se lave les mains, boit un grand verre d'eau, s'assoit.", "Dîner : {plat}.",
                                     "Josiane veut aller voir Claire à Pâques ; ils comptent les jours de fermeture.", "Ils parlent du cadeau de mardi. Il fait l'innocent.",
                                     "Débarrasse ; essuie la vaisselle.", "Range la vaisselle.", "Passe aux toilettes du rez-de-chaussée.",
                                     "Prend Le Progrès et s'installe dans son fauteuil.", "Allume la télévision."])):
    variante("soiree", v, textes_soir, [None, None, None, "C'est bon. Ça va bien comme ça.", None, None, None, None, None, None, None])

# commande du jeudi soir (après la caisse)
B["commande_jeudi"] = {"defaut": [
    {"titre": "Bon de commande du grossiste", "routine": "rt-commerce", "piece": "reserve", "lieu": "epicerie-chazal", "mode": "travail", "charge": "simple",
     "posture": "debout", "action": "Compte les cartons et les packs de la réserve, puis les rayons, le carnet de bons de commande à la main.", "via": ["boutique"]},
    {"titre": "Bon de commande du grossiste", "routine": "rt-commerce", "piece": "arriere-boutique", "lieu": "epicerie-chazal", "mode": "travail", "charge": "precision",
     "posture": "assis", "role": "commande_jeudi", "modele": "Remplit le bon de commande pour demain, 6 h 40, les lunettes sur le nez : {commande} ; {n_commande} lignes en tout.",
     "pensee": "Le samedi, ça part vite. Heureusement que le grossiste passe demain."},
]}

# samedi soir : belote avec les Morel
SB = copy.deepcopy(B["soiree"]["defaut"])
txt = ["Entre par le garage, pose ce qu'il rapporte sur la table de la cuisine, accroche sa veste.", "Raconte sa journée à Josiane : l'horloger, Ahmed et son pain trop cuit.",
       "Se lave les mains, boit un grand verre d'eau, s'assoit.", "La pizza de Josiane, un verre de côtes-du-rhône.", "Finit sa part de pizza.",
       "Josiane prépare un saladier de bugnes pour les Morel.", "Débarrasse ; essuie la vaisselle.", "Range la vaisselle.", "Passe aux toilettes du rez-de-chaussée.",
       "Prend Le Progrès et s'installe dans son fauteuil.", "Sort le jeu de cartes et le carnet des scores du tiroir du buffet, les pose sur la table de la salle à manger."]
for k, t in enumerate(txt):
    SB[k]["action"] = t
    SB[k].pop("pensee", None)
SB[3]["pensee"] = "La pizza du samedi. Trente ans aussi."
SB[10] = {"titre": "Belote avec les Morel", "routine": "rt-samedi", "piece": "sejour", "lieu": "domicile", "mode": "eveille", "charge": "simple", "posture": "debout",
          "action": txt[10], "objets": [["obj-jeu-de-cartes", "sejour / table de salle à manger"]]}
B["soiree_samedi"] = {"defaut": SB}
B["belote"] = {"defaut": {
    "arrivee": {"titre": "Belote avec les Morel", "routine": "rt-samedi", "piece": "sejour", "lieu": "domicile", "mode": "eveille", "charge": "simple", "posture": "debout",
                "action": "On sonne : Gérard et Monique Morel, une bouteille de Saint-Joseph sous le bras. Robert débouche, sert quatre verres.",
                "pensee": "Gérard a mis sa casquette des Verts. Il le fait exprès.", "ev": ["bavardage_voisin", "rire"], "effets": {"social": 3}},
    "partie": {"titre": "Belote avec les Morel", "routine": "rt-samedi", "piece": "sejour", "lieu": "domicile", "mode": "loisir", "charge": "lecture", "posture": "assis",
               "effets": {"social": 1.5}},
    "depart": {"titre": "Belote avec les Morel", "routine": "rt-samedi", "piece": "sejour", "lieu": "domicile", "mode": "eveille", "charge": "simple", "posture": "debout",
               "action": "Les Morel repartent en traversant la rue. Robert range les cartes et le carnet des scores dans le tiroir du buffet.", "effets": {"social": 1.0},
               "objets": [["obj-jeu-de-cartes", "sejour / tiroir du buffet"]]},
}}

# dimanche : fermeture à midi, déjeuner, vote, randonnée, soirée
B["fermeture_dimanche"] = {"defaut": copy.deepcopy(B["fermeture_midi"]["defaut"]) + [copy.deepcopy(B["fermeture_soir"]["defaut"][2])]}
FD = B["fermeture_dimanche"]["defaut"]
FD[0]["action"] = "Baisse le rideau de fer à midi pile, éteint la radio et la caisse."
FD[1]["role"] = "caisse_soir"
FD[1]["modele"] = "Compte la caisse du dimanche au bureau : {especes} en espèces, qu'il range dans la sacoche du coffre pour la banque de demain. La matinée fait {recette_jour}. Rince la tasse."
FD[1].pop("pensee", None)
FD[1]["titre"] = "Fermeture du dimanche"; FD[0]["titre"] = "Fermeture du dimanche"; FD[2]["titre"] = "Fermeture du dimanche"
FD[2]["routine"] = FD[1]["routine"] = FD[0]["routine"] = "rt-dimanche"
FD[2]["modele"] = "Remplit {contenant} pour Josiane : {liste}, et les deux baguettes mises de côté. Glisse Le Progrès dessus, éteint la boutique."

base = {"titre": "Fin de semaine à la boutique", "routine": "rt-dimanche", "piece": "boutique", "lieu": "epicerie-chazal", "mode": "travail",
        "charge": "simple", "posture": "debout"}
def st(action, pensee=None, **kw):
    d = dict(base); d["action"] = action
    if pensee: d["pensee"] = pensee
    d.update(kw); return d
B["fin_de_semaine"] = {"defaut": [
    st("Trie les produits frais de la vitrine réfrigérée : {perimes} partent à la poubelle.", "Faut que je commande moins de frais. Je le dis chaque semaine.",
       role="perimes", modele="Trie les produits frais de la vitrine réfrigérée, rideau baissé : {perimes} partent à la poubelle."),
    st("Balaie la boutique, du fond vers la porte, et sous les rayons.", mode="effort", ev=["effort_physique"]),
    st("Passe la serpillière dans la boutique et dans la réserve.", "Le dos. Demain, rien. Demain, c'est lundi.", mode="effort", via=["reserve", "arriere-boutique"],
       ev=["mal_de_dos"]),
    st("Essuie les clayettes de la vitrine réfrigérée et nettoie l'étal des fruits et légumes, les dates les plus courtes devant.", via=["reserve"]),
    st("S'assoit au bureau de l'arrière-boutique avec le cahier des comptes, les lunettes sur le nez : additionne la semaine.", piece="arriere-boutique",
       posture="assis", charge="precision", role="comptes_semaine", objets=[["obj-lunettes", "sur son nez"]],
       modele="S'assoit au bureau de l'arrière-boutique avec le cahier des comptes, les lunettes sur le nez : la semaine fait {semaine}, cartes comprises.",
       modele_pensee="{semaine}. Avant la supérette, je faisais deux mille trois cents.", ev=["constat_chiffre"]),
    st("Remplit le bon de commande pour mardi : {commande}.", piece="arriere-boutique", posture="assis", charge="precision", role="commande_dimanche",
       modele="Remplit le bon de commande pour mardi : {commande}."),
    st("Termine le bon de commande.", "Voilà la semaine bouclée. Demain, congé.", piece="arriere-boutique", posture="assis", charge="precision", role="commande_fin",
       objets=[["obj-lunettes", "sur son front"]], ev=["comptes_faits"],
       modele="Termine le bon de commande : {n_commande} lignes pour la livraison de mardi, 6 h 40. Le pose sous l'agrafeuse et remonte ses lunettes."),
]}

DJ = []
base = {"titre": "Déjeuner du dimanche", "routine": "rt-dimanche", "piece": "cuisine", "lieu": "domicile", "mode": "eveille", "charge": "repos", "posture": "assis"}
def st(action, pensee=None, **kw):
    d = dict(base); d["action"] = action
    if pensee: d["pensee"] = pensee
    d.update(kw); return d
DJ = [st("Entre par le garage, pose les courses sur la table, accroche sa veste. Ça sent le rôti dans toute la maison.", posture="debout", role="arrivee_maison", effets={"social": 1.0}),
      st("Se lave les mains, boit un verre d'eau, aide Josiane à mettre la table du séjour.", posture="debout", charge="simple", effets={"soif": 20, "hygiene": 10}),
      st("Passent à table dans le séjour, la nappe des dimanches.", piece="sejour", ev=["moment_josiane"], effets={"social": 1.0}),
      st("Le rôti de bœuf et le gratin dauphinois.", "Pas de vin aujourd'hui. Je conduis tout à l'heure.", piece="sejour", repas="dejeuner", ev=["plaisir_simple"],
         effets={"faim": 55, "social": 1.0}),
      st("Ressert du gratin. Josiane parle de Claire et des petits.", piece="sejour", ev=["pensee_claire"], effets={"social": 1.0}),
      st("Racontent leur semaine : le cinéma, le match, la belote d'hier soir.", piece="sejour", effets={"social": 1.0}, ev=["rire"]),
      st("La tarte aux pommes de Josiane.", "Ses tartes. Rien à voir avec celles de la boulangerie.", piece="sejour", effets={"faim": 10, "social": 1.0}),
      st("Le café, à table.", piece="sejour", effets={"cafe": True, "soif": 10, "social": 1.0}, consommation=[["cafe_moulu", 14]]),
      st("Parlent du cadeau de mardi, à demi-mot. Il fait l'innocent.", "Trente-quatre ans. Elle sait que j'ai rien. Elle sait toujours.", piece="sejour",
         ev=["anniversaire_mariage"], effets={"social": 1.0}),
      st("Débarrasse la table du séjour.", piece="sejour", posture="debout", charge="simple"),
      st("Essuie la vaisselle pendant que Josiane lave.", posture="debout", charge="simple", effets={"social": 1.0}),
      st("Range la vaisselle.", posture="debout", charge="simple"),
      st("Passe aux toilettes du rez-de-chaussée.", piece="wc", posture="debout", charge="simple", effets={"toilettes": "vide"}),
      st("S'installe dans son fauteuil.", piece="sejour", charge="repos")]
B["dejeuner_dimanche"] = {"defaut": DJ}
base = {"titre": "Sieste", "routine": "rt-repos", "piece": "sejour", "lieu": "domicile", "mode": "sieste", "charge": "sommeil", "posture": "assis"}
B["sieste_dimanche"] = {"defaut": [st("S'endort dans son fauteuil, les mains croisées sur le ventre.")] + [st("Somnole.") for _ in range(2)]}
base = {"titre": "Vote", "routine": "rt-dimanche", "piece": "entree", "lieu": "domicile", "mode": "eveille", "charge": "simple", "posture": "debout"}
B["vote"] = {"defaut": [
    st("Se réveille. Josiane a déjà son manteau : « On va voter, et après tu mets tes chaussures. » Prend sa veste et son portefeuille avec sa carte d'électeur.",
       role="depart_vote", objets=[["obj-veste", "porté"], ["obj-portefeuille", "poche de la veste"], ["obj-cles", "poche de la veste"]]),
    st("Marche avec Josiane jusqu'à l'école du quartier, bras dessus bras dessous.", piece="rue des Glycines", lieu="exterieur", posture="en marche", sortie="rue-maison",
       parcours=[{"moyen": "marche", "distance_m": 400, "denivele_m": 0}], ev=["sortie_couple"], effets={"social": 1.0}),
    st("Dans le préau de l'école, prend les bulletins, passe dans l'isoloir, glisse l'enveloppe dans l'urne et signe la liste d'émargement. Salue les assesseurs, des voisins.",
       "On vote. C'est la moindre des choses.", piece="bureau de vote, préau de l'école", lieu="bureau-de-vote", effets={"social": 2}, ev=["bavardage_voisin"]),
    st("Rentre à pied avec Josiane en parlant des listes.", piece="rue des Glycines", lieu="exterieur", posture="en marche",
       parcours=[{"moyen": "marche", "distance_m": 400, "denivele_m": 0}], effets={"social": 1.0}),
]}
base = {"titre": "Départ pour les monts d'Or", "routine": "rt-dimanche", "piece": "entree", "lieu": "domicile", "mode": "eveille", "charge": "simple", "posture": "debout"}
B["preparation_randonnee"] = {"defaut": [
    st("Rentre par la porte d'entrée, chausse ses chaussures de marche, met sa casquette de toile.", retour="rue-maison",
       objets=[["obj-chaussures-marche", "aux pieds"], ["obj-casquette", "sur la tête"]]),
    st("Prend au garage le sac à dos avec la gourde et les jumelles, les clés de la Kangoo, ouvre la porte basculante. Josiane monte à côté de lui.", piece="garage",
       objets=[["obj-sac-a-dos", "dans le coffre de la Kangoo"], ["obj-cles-kangoo", "dans sa main"]], effets={"soif": 10, "social": 1.0}),
]}
base = {"titre": "Randonnée dans les monts d'Or", "routine": "rt-dimanche", "piece": "chemin du mont Thou", "lieu": "monts-d-or", "mode": "effort", "charge": "simple",
        "posture": "en marche", "effets": {"social": 1.0}}
def m(d, den=0):
    return [{"moyen": "marche", "distance_m": d, "denivele_m": den}]
B["randonnee"] = {"defaut": [
    st("Gare la Kangoo sur le parking de Poleymieux, met le sac à dos sur ses épaules. Josiane noue son foulard.", piece="parking de Poleymieux", mode="eveille", posture="debout",
       role="debut_randonnee", objets=[["obj-sac-a-dos", "sur le dos"], ["obj-cles-kangoo", "poche de la veste"], ["obj-kangoo", "parking de Poleymieux"]]),
    st("Prend le chemin qui monte vers le mont Thou, entre les murets de pierre dorée.", parcours=m(300, 20), ev=["effort_physique", "nature"]),
    st("Monte à son pas, Josiane devant.", parcours=m(300, 25)),
    st("Le chemin entre dans les bois ; des primevères sur le talus.", "Josiane dit le nom de chaque fleur. Moi, je connais les radis.", parcours=m(300, 25), ev=["nature"]),
    st("Monte en soufflant.", parcours=m(250, 25), ev=["effort_physique"]),
    st("S'arrête au tournant pour reprendre son souffle, boit à la gourde.", posture="debout", mode="eveille", effets={"soif": 20, "social": 1.0}),
    st("Repart. Le chemin devient caillouteux.", parcours=m(300, 30)),
    st("Monte.", parcours=m(300, 30), ev=["effort_physique"]),
    st("Les antennes du sommet apparaissent entre les arbres.", parcours=m(300, 25)),
    st("Arrive près du sommet du mont Thou, les jambes lourdes.", "Six cents mètres. Le Bernabéu, c'est rien à côté.", parcours=m(300, 25), ev=["effort_physique"]),
    st("Sur le replat, regarde Lyon à ses pieds, la Saône, la colline de Fourvière. Prend les jumelles.", "On voit la Croix-Rousse. Ma boutique est là-dedans, quelque part.",
       piece="mont Thou", posture="debout", mode="eveille", ev=["nature"]),
    st("S'assoit sur un banc de pierre avec Josiane, mange un carré de chocolat qu'elle a apporté.", piece="mont Thou", posture="assis", mode="eveille",
       ev=["moment_josiane", "plaisir_simple"], effets={"faim": 3, "social": 1.0}),
    st("Repart sur le chemin des crêtes, vers le mont Cindre.", parcours=m(300, -10)),
    st("Marche sur la crête ; le vent est frais.", parcours=m(300, 0), ev=["nature"]),
    st("Marche.", parcours=m(300, -10)),
    st("Croise un couple avec un chien ; bonjour, bonjour.", parcours=m(300, -15)),
    st("Marche en parlant de Claire et des petits.", "Lucas pourrait venir marcher ici, cet été. Avec un bâton.", parcours=m(300, -15), ev=["pensee_claire"]),
    st("Arrive au mont Cindre, près de l'ermitage et de ses grottes.", piece="mont Cindre", parcours=m(300, -10)),
    st("Regarde les grottes de l'ermitage ; Josiane lit le panneau à voix haute.", piece="mont Cindre", posture="debout", mode="eveille"),
    st("Boit à la gourde, s'étire le dos.", "Le dos tient. Il tient.", piece="mont Cindre", posture="debout", mode="eveille", effets={"soif": 20, "social": 1.0}),
    st("Prend la descente vers Poleymieux.", piece="chemin du retour", parcours=m(300, -30)),
    st("Descend, en retenant ses pas.", piece="chemin du retour", parcours=m(300, -35), ev=["effort_physique"]),
    st("Descend ; les genoux tirent.", "À la descente, c'est les genoux. À la montée, le souffle. À mon âge, tout.", piece="chemin du retour", parcours=m(300, -35)),
    st("Traverse un pré ; des chevaux s'approchent de la clôture.", piece="chemin du retour", parcours=m(300, -20), ev=["nature"]),
    st("Descend vers le village.", piece="chemin du retour", parcours=m(300, -25)),
    st("Les premières maisons de Poleymieux.", piece="chemin du retour", parcours=m(250, -10)),
    st("Rejoint le parking, pose le sac dans le coffre de la Kangoo.", "Huit kilomètres. Je les sentirai demain.", piece="parking de Poleymieux", parcours=m(200, 0),
       ev=["repos_merite"], objets=[["obj-sac-a-dos", "dans le coffre de la Kangoo"]]),
]}
base = {"titre": "Retour des monts d'Or", "routine": "rt-dimanche", "piece": "entree", "lieu": "domicile", "mode": "eveille", "charge": "simple", "posture": "debout"}
B["retour_randonnee"] = {"defaut": [
    st("Rentre la Kangoo au garage, range le sac à dos sur l'étagère. Enlève ses chaussures de marche pleines de terre, les laisse sur le paillasson du garage, accroche sa veste et sa casquette, pose les clés.",
       role="arrivee_randonnee", objets=[["obj-kangoo", "garage / place de la Kangoo"], ["obj-sac-a-dos", "garage / étagère"], ["obj-chaussures-marche", "garage / paillasson"],
                                         ["obj-casquette", "entree / portemanteau"], ["obj-veste", "entree / portemanteau"], ["obj-cles-kangoo", "entree / vide-poche"],
                                         ["obj-cles", "entree / vide-poche"], ["obj-portefeuille", "entree / vide-poche"]]),
]}
base = {"titre": "Fin d'après-midi", "routine": "rt-dimanche", "piece": "sejour", "lieu": "domicile", "mode": "lecture", "charge": "lecture", "posture": "assis"}
B["fin_dimanche"] = {"defaut": [
    st("Boit deux grands verres d'eau à la cuisine.", piece="cuisine", posture="debout", mode="eveille", charge="simple", effets={"soif": 40}),
    st("Passe aux toilettes du rez-de-chaussée.", piece="wc", posture="debout", mode="eveille", charge="simple", effets={"toilettes": "vide"}),
    st("Prend une douche à l'étage, se change.", piece="salle-de-bain", posture="debout", mode="eveille", charge="simple", effets={"hygiene": 70}),
    st("Redescend, allume la radio de la cuisine, s'installe dans son fauteuil avec Le Progrès.", role="journal_dimanche", radio=True, app={"allume": ["radio-cuisine"]},
       ev=["lecture_journal"], objets=[["JOURNAL", "sejour / dans sa main"], ["obj-lunettes", "sur son nez"], ["JOURNAL_VEILLE", "sejour / sous la table basse"]]),
    st("Lit les pages régionales, les jambes allongées sur le pouf.", "Les jambes. Mais c'était bien.", radio=True),
    st("La radio donne les premières estimations des régionales.", radio=True),
    st("Fait les mots croisés du journal.", radio=True),
    st("Fait les mots croisés.", radio=True),
    st("Regarde la photo de Claire et des petits sur le buffet.", "Pâques. On ira à Grenoble, cette fois.", radio=True, ev=["pensee_claire"]),
    st("Pense au cadeau de mardi.", "Une montre ? L'horloger pourrait m'en conseiller une. Tiens.", radio=True, ev=["anniversaire_mariage"]),
    st("Fait les mots croisés.", radio=True),
    st("Somnole un peu, le journal sur les genoux.", radio=True, mode="sieste", charge="sommeil"),
    st("Se réveille ; Josiane met le couvert.", radio=True, effets={"social": 1.0}),
    st("Pose le journal sur la table basse, remonte ses lunettes.", radio=True, objets=[["JOURNAL", "sejour / table basse"], ["obj-lunettes", "sur son front"]]),
    st("La nuit tombe ; il allume la lampe du séjour.", radio=True, app={"allume": ["lumiere-sejour"]}),
    st("Met la table dans la cuisine.", piece="cuisine", posture="debout", mode="eveille", charge="simple", radio=True),
    st("Remplit la carafe d'eau.", piece="cuisine", posture="debout", mode="eveille", charge="simple", radio=True, effets={"soif": 15}),
]}
base = {"titre": "Dîner du dimanche", "routine": "rt-repas", "piece": "cuisine", "lieu": "domicile", "mode": "eveille", "charge": "repos", "posture": "assis"}
B["diner_dimanche"] = {"defaut": [
    st("Éteint la radio. Les restes du midi avec Josiane.", app={"eteint": ["radio-cuisine"]}, ev=["moment_josiane"], effets={"social": 1.0}),
    st("Le rôti froid, le comté, un verre de vin.", repas="diner", effets={"faim": 40, "soif": 10, "social": 1.0}),
    st("Josiane suit les résultats des régionales à la radio portative.", effets={"social": 1.0}),
    st("Finit son assiette.", effets={"social": 1.0}),
    st("Débarrasse ; essuie la vaisselle.", posture="debout", charge="simple", effets={"social": 1.0}),
    st("Range la vaisselle.", posture="debout", charge="simple"),
    st("Passe aux toilettes du rez-de-chaussée.", piece="wc", posture="debout", charge="simple", effets={"toilettes": "vide"}),
    st("S'installe dans son fauteuil.", piece="sejour", charge="repos"),
    st("Allume la télévision : les soirées électorales.", piece="sejour", mode="loisir", tele=True, app={"allume": ["television"]},
       objets=[["obj-telecommande", "sejour / dans sa main"]]),
]}

# trajets : textes de jeudi à dimanche et trajets nouveaux
R["aube"]["jeudi"] = {"textes": ["Sort la Kangoo, éteint le garage. Cours Émile-Zola désert ; il bâille à chaque feu.", "Pont Winston-Churchill. Il ouvre la vitre pour se réveiller.",
                                 "Montée de la Boucle, boulevard, cour de l'épicerie."], "pensees": ["Le but de Pjanić. Je le revois encore.", None, None], "ev": [["souvenir_excitant"], [], []]}
R["aube"]["samedi"] = {"textes": ["Sort la Kangoo, éteint le garage. Cours Émile-Zola, vide.", "Pont Winston-Churchill ; un rameur sur le Rhône.", "Montée de la Boucle, boulevard, cour de l'épicerie."],
                       "pensees": [None, None, None], "ev": [["conduite_tranquille"], [], []]}
R["aube"]["dimanche"] = {"textes": ["Sort la Kangoo, éteint le garage. Villeurbanne dort.", "Pont Winston-Churchill, désert.", "Montée de la Boucle, boulevard, cour de l'épicerie."],
                         "pensees": [None, None, None], "ev": [["conduite_tranquille"], [], []]}
R["midi_dimanche"] = {"defaut": {"textes": ["Raccroche sa blouse, remet sa veste, sort par la cour, le cabas sur le siège. Descend la montée de la Boucle.",
                                            "Pont Winston-Churchill ; des familles se promènent sur les quais.", "Cours Émile-Zola, rue des Glycines ; rentre la Kangoo au garage."],
                                 "pensees": [None, "Dimanche midi. Le rôti de Josiane.", None], "ev": [[], ["conduite_tranquille"], []]}}
R["monts_aller"] = {"defaut": {"textes": ["Sort la Kangoo, éteint le garage. Rue des Glycines, puis le boulevard Laurent-Bonnevay vers le nord.",
                                          "Traverse le Rhône, file vers Caluire.", "Longe la Saône par Collonges.", "Quitte la Saône, monte vers Saint-Romain.",
                                          "Monte dans les monts d'Or, virage après virage, entre les murets de pierre dorée.", "Arrive à Poleymieux."],
                               "pensees": [None, None, "La Saône, c'est l'horloger qui court le long, le matin.", None, None, None],
                               "ev": [["sortie_couple"], [], ["conduite_tranquille"], [], ["nature"], []]}}
R["monts_retour"] = {"defaut": {"textes": ["Quitte le parking de Poleymieux, redescend les virages.", "Descend vers la Saône.", "Longe la Saône, puis Caluire.",
                                           "Traverse le Rhône, boulevard Laurent-Bonnevay.", "Villeurbanne ; Josiane somnole à côté de lui.", "Rue des Glycines ; rentre la Kangoo au garage."],
                                "pensees": [None, None, None, None, "Une bonne journée. Les jambes, mais une bonne journée.", None],
                                "ev": [[], [], ["conduite_tranquille"], [], ["moment_josiane"], []]}}

# ------------------------------------------------------------------ écriture
for k in list(B):
    if k == "routes":
        continue
B["principe"] = ("Scènes de la vie de Robert : chaque scène est une suite de pas (texte, pièce, posture, objets, appareils, effets). Les scènes du lundi au mercredi "
                 "sont reprises des journées de référence ; celles de jeudi à dimanche sont rédigées pour l'agent. « variante » : texte du jour, mêmes gestes. "
                 "« role » : pas que l'agent complète d'après l'état (livraisons, caisse, prélèvements, journal…). JOURNAL et JOURNAL_VEILLE désignent Le Progrès "
                 "du jour et celui de la veille.")
json.dump(B, open(os.path.join(RACINE, "data", "agents", "robert-chazal", "blocs.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("blocs :", len(B))
