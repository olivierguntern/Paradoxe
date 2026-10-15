"""Prépare les données de la vue du quartier façon Sims (vue/sims.html → vue/sims.js).

Usage : python3 outils/exporter_sims.py [--quartier data/quartier] [--sortie vue/sims.js]

Lit les plans des logements (data/monde/croix-rousse.json et data/monde/plans.json)
et les journées du quartier. Les logements sont regroupés en terrains (« lots ») :
l'épicerie et l'appartement des Vial au-dessus, la maison des Chazal, celle des
Morel, l'appartement de Thomas.

Pour chaque pas de chaque habitant :
- où il est : terrain, étage, pièce (ou dehors, et où) ;
- l'endroit précis : le meuble que nomme l'action du catalogue (« lieu » :
  évier, canapé, lit…) dans sa pièce, sinon la place prévue pour sa posture
  (« postes » du plan), sinon le milieu de la pièce ; deux habitants au même
  endroit se décalent ;
- sa pose (debout, assis, allongé, en marche), sa direction ;
- le chemin depuis le pas précédent, porte par porte ;
- ce qu'il fait, ce qu'il pense, ses besoins et son humeur ;
- les pièces éclairées ;
- son geste (cuisiner, manger, lire, travailler de ses mains, faire le ménage…),
  pour l'animer.

Dehors, deux terrains de rue : la Croix-Rousse (rue d'Austerlitz, place,
boulevard, Grande-Rue) et la rue des Glycines à Villeurbanne, dans le repère
de data/monde/croix-rousse.json. Un habitant y est à un endroit connu (le
marché, le Clos Jouve, le tabac, l'école…) ou en chemin entre deux (sa porte,
un endroit connu) : sa position avance avec le trajet. En voiture, en bus, ou
loin (Vienne, le cinéma), il n'est pas montré.
"""
import argparse
import json
import math
import os
import sys
import unicodedata
import zlib

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fiches import charger

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONDE = os.path.join(RACINE, "data", "monde")
BESOINS = ["faim", "soif", "energie", "hygiene", "toilettes", "social", "detente"]
POSES = {"debout": 0, "assis": 1, "allongé": 2, "en marche": 3, "en course": 3}
COULEURS = {"thomas-berthier": "#3f7fbf", "robert-chazal": "#c0573a", "josiane-chazal": "#b5559b", "gerard-morel": "#5d8f3c",
            "monique-morel": "#d39b2a", "henri-vial": "#6c6f9e", "simone-vial": "#2f9c94"}
LOTS = [
    {"id": "epicerie", "nom": "L'épicerie et les Vial", "adresse": "Grande-Rue de la Croix-Rousse",
     "parts": [("croix", "boutique-robert", 0, "epicerie-chazal"), ("plans", "appartement-vial", 1, "appartement-vial")], "hauteur": 3.4},
    {"id": "maison-chazal", "nom": "La maison des Chazal", "adresse": "rue des Glycines, Villeurbanne",
     "parts": [("croix", "maison-robert", 0, "maison-chazal")], "hauteur": 2.7},
    {"id": "maison-morel", "nom": "La maison des Morel", "adresse": "rue des Glycines, Villeurbanne",
     "parts": [("plans", "maison-morel", 0, "maison-morel")], "hauteur": 2.6},
    {"id": "thomas", "nom": "L'appartement de Thomas", "adresse": "rue d'Austerlitz, 3e étage",
     "parts": [("croix", "domicile-thomas", 0, "domicile-thomas")], "hauteur": 2.9},
]
ZONES = {"trottoir", "cour-epicerie", "rue-maison", "jardin", "palier", "porte-immeuble"}

# ------------------------------------------------------------------ gestes (pour animer les personnages)
GESTES = {"cuisiner": 1, "petit_dejeuner": 2, "collation": 2, "pause_fruit": 2, "repas_dehors": 2, "lecture": 3, "lecture_lit": 3,
          "lecture_technique": 3, "lecture_dehors": 3, "planification": 3, "travail": 4, "travail_personnel": 4, "bricolage": 4,
          "bricolage_maison": 4, "jardinage": 4, "travail_bureau": 4, "menage": 5, "vaisselle": 5, "rangement_cuisine": 5, "lessive": 5,
          "etendage": 5, "rangement_atelier": 5, "television": 6, "match": 6, "cinema": 6, "tenir_boutique": 7, "travail_boutique": 7,
          "ouverture_boutique": 7, "fermeture_boutique": 7, "recette_coffre": 7, "douche": 8, "toilette_matin": 8, "toilette_soir": 8,
          "belote": 9, "pause_cafe": 10, "cafe_vaisselle": 10, "boire": 10, "boules": 11, "chorale": 12, "messe": 12, "visite": 13,
          "courses_quartier": 13}

# ------------------------------------------------------------------ dehors : deux terrains de rue, dans le repère du monde
RUES = [
    {"id": "croix-rousse", "nom": "La Croix-Rousse", "adresse": "le plateau : rue d'Austerlitz, place, boulevard, Grande-Rue", "cadre": [-190, -175, 980, 270],
     "rues": ["rue-austerlitz", "rue-liaison", "boulevard", "grande-rue", "montee-boucle"], "bati": "immeubles"},
    {"id": "glycines", "nom": "La rue des Glycines", "adresse": "Villeurbanne, quartier de Cusset", "cadre": [4430, -330, 4790, 270],
     "rues": ["rue-des-glycines", "cours-emile-zola"], "bati": "maisons"},
]
# endroits connus, dehors : terrain, x, y (et ce qui s'y voit)
ENDROITS = {
    "marche-croix-rousse": ("croix-rousse", 560, -121, "le marché du boulevard"), "tabac-garnier": ("croix-rousse", 336, 180, "le tabac de M. Garnier"),
    "clos-jouve": ("croix-rousse", 690, -138, "le boulodrome du Clos Jouve"), "eglise-saint-denis": ("croix-rousse", 322, 252, "l'église Saint-Denis"),
    "bibliotheque-croix-rousse": ("croix-rousse", 105, -132, "la bibliothèque"), "bureau-de-vote-4e": ("croix-rousse", 200, -98, "la mairie du 4e"),
    "bureau-de-vote": ("croix-rousse", 200, -98, "la mairie du 4e"), "chez-mme-perrin": ("croix-rousse", 226, 58, "chez Mme Perrin"),
    "gros-caillou": ("croix-rousse", 938, -122, "le Gros Caillou"), "banque": ("croix-rousse", 362, -104, "la banque"),
    "commerces-cusset": ("glycines", 4712, 116, "les commerces de Cusset"), "cabinet-medical": ("glycines", 4538, 116, "le cabinet médical"),
    "parc-de-la-feyssine": ("glycines", 4480, 215, "le parc de la Feyssine"), "rue-des-glycines": ("glycines", 4596, -235, "la rue des Glycines"),
}
# la porte de chaque logement, dehors
PORTES = {"domicile-thomas": ("croix-rousse", 6.6, -5), "appartement-vial": ("croix-rousse", 337, 169), "epicerie-chazal": ("croix-rousse", 337, 172.5),
          "maison-chazal": ("glycines", 4604, -204), "maison-morel": ("glycines", 4604, -268)}
VEHICULES = {"trajet-voiture", "trajet-transports"}
# ce qui relie les rues entre elles là où le plan ne le dit pas (la place de la Croix-Rousse)
RACCORDS = {"croix-rousse": [[(262, -4.5), (300, 0), (326, 20), (332, 25)], [(262, -4.5), (300, -60), (334, -110)], [(332, 25), (334, -40), (334, -110)]],
            "glycines": []}


def reseau(R, W):
    """Le réseau des rues d'un terrain : sommets (points), arêtes (longueurs) ; les croisements de deux rues sont des sommets."""
    segs = []
    for r in W["rues"]:
        if r["id"] in R["rues"]:
            segs += list(zip(r["axe"], r["axe"][1:]))
    for ch in RACCORDS.get(R["id"], []):
        segs += list(zip(ch, ch[1:]))
    segs = [(tuple(a), tuple(b)) for a, b in segs]
    # chaque segment est coupé à ses croisements avec les autres
    coupes = {k: [0.0, 1.0] for k in range(len(segs))}
    for i, (a, b) in enumerate(segs):
        for j, (c, d) in enumerate(segs):
            if j <= i:
                continue
            den = (b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])
            if abs(den) < 1e-9:
                continue
            u = ((c[0] - a[0]) * (d[1] - c[1]) - (c[1] - a[1]) * (d[0] - c[0])) / den
            v = ((c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])) / den
            if -1e-6 <= u <= 1 + 1e-6 and -1e-6 <= v <= 1 + 1e-6:
                coupes[i].append(min(1, max(0, u))); coupes[j].append(min(1, max(0, v)))
    pts, index, aretes = [], {}, {}
    def sommet(q):
        k = (round(q[0], 1), round(q[1], 1))
        if k not in index:
            index[k] = len(pts); pts.append(k); aretes[index[k]] = []
        return index[k]
    for i, (a, b) in enumerate(segs):
        us = sorted(set(coupes[i]))
        q = [(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u) for u in us]
        for m, n in zip(q, q[1:]):
            x, y = sommet(m), sommet(n)
            l = math.dist(m, n)
            aretes[x].append((y, l)); aretes[y].append((x, l))
    return pts, aretes


def itineraire(R_res, A, B):
    """Le chemin à pied de A à B par les rues : jusqu'au point le plus proche d'une rue, le long des rues (plus court chemin), puis jusqu'à B."""
    import heapq
    pts, aretes = R_res
    if not pts:
        return [A, B]
    pts, aretes = list(pts), {k: list(v) for k, v in aretes.items()}
    def accrocher(P):
        """Un sommet de plus, sur l'arête la plus proche de P (au pied de la perpendiculaire)."""
        meilleur = None
        for x, voisins in list(aretes.items()):
            for y, l in voisins:
                if y < x or y >= len(pts) or x >= len(pts):
                    continue
                (ax, ay), (bx, by) = pts[x], pts[y]
                L2 = (bx - ax) ** 2 + (by - ay) ** 2 or 1e-9
                u = max(0, min(1, ((P[0] - ax) * (bx - ax) + (P[1] - ay) * (by - ay)) / L2))
                q = (ax + (bx - ax) * u, ay + (by - ay) * u)
                d = math.dist(P, q)
                if meilleur is None or d < meilleur[0]:
                    meilleur = (d, x, y, q)
        _, x, y, q = meilleur
        k = len(pts); pts.append(q); aretes[k] = [(x, math.dist(q, pts[x])), (y, math.dist(q, pts[y]))]
        aretes[x].append((k, math.dist(q, pts[x]))); aretes[y].append((k, math.dist(q, pts[y])))
        return k
    s, f = accrocher(A), accrocher(B)
    dist, prec, file = {s: 0}, {}, [(0, s)]
    while file:
        d, x = heapq.heappop(file)
        if x == f:
            break
        if d > dist.get(x, 1e18):
            continue
        for y, l in aretes[x]:
            if d + l < dist.get(y, 1e18):
                dist[y], prec[y] = d + l, x
                heapq.heappush(file, (d + l, y))
    chemin, x = [], f
    while x != s and x in prec:
        chemin.append(pts[x]); x = prec[x]
    chemin.append(pts[s])
    return [A] + chemin[::-1] + [B]


def le_long(chemin, u):
    """Le point (x, y) et la direction à la part u (0 à 1) du chemin."""
    L = sum(math.dist(a, b) for a, b in zip(chemin, chemin[1:])) or 1
    s = u * L
    for a, b in zip(chemin, chemin[1:]):
        l = math.dist(a, b)
        if s <= l or b is chemin[-1]:
            v = s / l if l else 0
            return a[0] + (b[0] - a[0]) * min(1, v), a[1] + (b[1] - a[1]) * min(1, v), math.atan2(b[1] - a[1], b[0] - a[0])
        s -= l
    return chemin[-1][0], chemin[-1][1], 0
TRAJETS = {"trajet-pied", "trajet", "trajet-epicerie"}


def norm(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def r2(v):
    return round(v, 2) + 0.0


def h01(*cle):
    return (zlib.crc32("|".join(map(str, cle)).encode()) % 10000) / 10000


class Textes:
    def __init__(self):
        self.liste, self.index = [], {}

    def __call__(self, t):
        t = t or ""
        if t not in self.index:
            self.index[t] = len(self.liste)
            self.liste.append(t)
        return self.index[t]


# ------------------------------------------------------------------ plans
def charger_plans():
    W = json.load(open(os.path.join(MONDE, "croix-rousse.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(MONDE, "plans.json"), encoding="utf-8"))
    croix = {l["id"]: l for l in W["logements"]}
    lots, ou = [], {}
    for n, L in enumerate(LOTS):
        lot = {"id": L["id"], "nom": L["nom"], "adresse": L["adresse"], "hauteur": L["hauteur"], "pieces": [], "portes": [], "fenetres": [], "mobilier": [], "postes": {}}
        for source, lid, niv0, logement in L["parts"]:
            plan = croix[lid] if source == "croix" else P[lid]
            for pid, pc in plan["pieces"].items():
                niv = pc.get("niveau") if pc.get("niveau") is not None else niv0
                zone = pc.get("zone", pid in ZONES)
                lot["pieces"].append({"id": f"{logement}/{pid}", "local": pid, "nom": pc.get("nom", pid.replace("-", " ")), "rect": pc["rect"], "niveau": niv, "zone": zone})
                ou[(logement, pid)] = (n, niv)
            niv_de = {p["local"]: p["niveau"] for p in lot["pieces"] if p["id"].startswith(logement + "/")}
            for d in plan.get("portes", []):
                a, b = d["entre"]
                seg = d.get("segment")
                if seg is None:   # un escalier intérieur : on passe par le milieu de la cage
                    r = plan["pieces"][a]["rect"]
                    seg = [[(r[0] + r[2]) / 2, (r[1] + r[3]) / 2]] * 2
                lot["portes"].append({"entre": [f"{logement}/{a}", f"{logement}/{b}"], "segment": seg, "escalier": bool(d.get("escalier")),
                                      "niveau": niv_de.get(b, niv_de.get(a, niv0))})
            for f in plan.get("fenetres", []):
                lot["fenetres"].append({"segment": f["segment"], "niveau": niv_de.get(f["piece"], niv0), "piece": f"{logement}/{f['piece']}"})
            for m in plan.get("mobilier", []):
                lot["mobilier"].append({"nom": m["nom"], "piece": f"{logement}/{m['piece']}", "boite": m["boite"], "z": m.get("z", 0),
                                        "niveau": niv_de.get(m["piece"], niv0)})
            for pid, postes in (plan.get("postes") or {}).items():
                if pid != "principe":
                    lot["postes"][f"{logement}/{pid}"] = postes
        lots.append(lot)
    return lots, ou


# ------------------------------------------------------------------ où est-il
def logement_de(pid, s, fiche):
    """(logement, pièce locale) du pas, ou None s'il est dehors."""
    piece, lieu = s["piece"], s.get("lieu")
    if ":" in piece:
        return tuple(piece.split(":", 1))
    if lieu == "domicile":
        lds = fiche["domicile"]["plan"].get("logements_des_sites", {})
        pc = next((p for p in fiche["domicile"]["pieces"] if p["id"] == piece), None)
        if pid == "thomas-berthier":
            return ("domicile-thomas", piece)
        if pc:
            return (pc.get("logement") or lds.get(pc.get("lieu")) or "maison-chazal", pc.get("id_local", piece))
        # un endroit du plan qui n'est pas une pièce de sa fiche (le jardin) : chez lui
        return (next(iter(lds.values()), "maison-chazal"), piece)
    return (lieu, piece)


def actions_lieux():
    """Texte d'action du catalogue → mot du lieu (meuble) où elle se fait ; le plus long d'abord."""
    A = json.load(open(os.path.join(MONDE, "actions.json"), encoding="utf-8"))["actions"]
    paires = {}
    for a in A.values():
        if a.get("texte") and a.get("lieu"):
            paires[a["texte"]] = a["lieu"]
        for ph in a.get("phases", []) if isinstance(a.get("phases"), list) else []:
            if ph.get("texte"):
                l = ph.get("lieu", a.get("lieu"))
                if l:
                    paires[ph["texte"]] = l
    paires["Passe aux toilettes"] = "wc"
    return sorted(paires.items(), key=lambda x: -len(x[0]))


def actions_gestes():
    """Texte d'action du catalogue → code de geste (le repas : préparer, puis manger) ; le plus long d'abord."""
    A = json.load(open(os.path.join(MONDE, "actions.json"), encoding="utf-8"))["actions"]
    paires = {}
    for aid, a in A.items():
        code = GESTES.get(aid, 0)
        if a.get("texte"):
            paires[a["texte"]] = code
        for k, ph in enumerate(a.get("phases", []) if isinstance(a.get("phases"), list) else []):
            if ph.get("texte"):
                paires[ph["texte"]] = (1 if k == 0 else 2) if aid == "repas" else (0 if ph.get("trajet") else code)
    return sorted(paires.items(), key=lambda x: -len(x[0]))


def batir(R, W):
    """Le terrain de rue : rues, places, bâtiments (les connus, et des immeubles ou des maisons le long des rues), endroits connus."""
    x0, y0, x1, y1 = R["cadre"]
    rues = [{"axe": r["axe"], "largeur": r.get("facade_a_facade", 10)} for r in W["rues"] if r["id"] in R["rues"]]
    connus = []
    if R["id"] == "croix-rousse":
        connus += [{"rect": [-3, 0, 13.5, 14], "h": 15, "couleur": "#d9b48c", "nom": "l'immeuble de Thomas"},
                   {"rect": [338, 164, 350, 176], "h": 13.6, "couleur": "#e8c9a0", "nom": "l'épicerie Chazal et les Vial", "enseigne": "#b5402f"},
                   {"rect": [338, 176, 350, 186], "h": 13, "couleur": "#d8b08a", "nom": "le tabac", "enseigne": "#c0392b"},
                   {"rect": [282, 236, 314, 262], "h": 18, "couleur": "#cfc6b4", "nom": "l'église Saint-Denis", "clocher": True}]
        for rb in W.get("reperes_batis", []):
            a, b, c, d = rb["rect"]
            if x0 <= a <= x1 and y0 <= b <= y1:
                connus.append({"rect": [a, b, c, d], "h": rb.get("h", 10), "couleur": "#c9c2b5", "nom": rb["nom"]})
    else:
        connus += [{"rect": [4606, -209.5, 4614.5, -200], "h": 6.5, "couleur": "#e6d3b3", "nom": "la maison des Chazal", "toit": True},
                   {"rect": [4606, -275, 4616, -262], "h": 3.6, "couleur": "#efe2c4", "nom": "la maison des Morel", "toit": True},
                   {"rect": [4648, 158, 4690, 190], "h": 8, "couleur": "#d9cdb8", "nom": "l'école (bureau de vote)"},
                   {"rect": [4690, 120, 4740, 136], "h": 7, "couleur": "#d7b98c", "nom": "les commerces de Cusset", "enseigne": "#2f7fd1"},
                   {"rect": [4520, 120, 4556, 136], "h": 8, "couleur": "#e3e0d8", "nom": "le cabinet médical", "enseigne": "#3fae49"}]
    zones = []
    if R["id"] == "croix-rousse":
        zones += [{"rect": [470, -126, 650, -116], "couleur": "#d9c6a0", "nom": "marché", "etals": True},
                  {"rect": [665, -150, 715, -128], "couleur": "#d8c49a", "nom": "Clos Jouve"},
                  {"rect": [262, -94, 405, 25], "couleur": "#b9b3a6", "nom": "place de la Croix-Rousse"}]
    else:
        zones += [{"rect": [4440, 170, 4525, 262], "couleur": "#7fb35a", "nom": "parc de la Feyssine", "arbres": True}]

    def libre(r):
        a, b, c, d = r
        if a < x0 or c > x1 or b < y0 or d > y1:
            return False
        for k in connus + zones:
            ka, kb, kc, kd = k["rect"]
            if a < kc + 2 and c > ka - 2 and b < kd + 2 and d > kb - 2:
                return False
        for ru in rues:
            for (ax, ay), (bx, by) in zip(ru["axe"], ru["axe"][1:]):
                w = ru["largeur"] / 2 + 0.5
                if a < max(ax, bx) + w and c > min(ax, bx) - w and b < max(ay, by) + w and d > min(ay, by) - w:
                    return False
        return True
    batiments = list(connus)
    maison = R["bati"] == "maisons"
    for r in W["rues"]:
        if r["id"] not in R["rues"] or not r.get("bati"):
            continue
        w = r.get("facade_a_facade", 10) / 2
        for (ax, ay), (bx, by) in zip(r["axe"], r["axe"][1:]):
            L = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / L, (by - ay) / L
            for cote in (-1, 1):
                s = 2.0
                while s < L - 6:
                    lg = (9 + 5 * h01(r["id"], s, cote)) if maison else (13 + 12 * h01(r["id"], s, cote))
                    pr = 10 if maison else 12 + 4 * h01(cote, s, r["id"])
                    off = w + (5 if maison else 1.0)
                    cx, cy = ax + ux * (s + lg / 2) + (-uy) * cote * (off + pr / 2), ay + uy * (s + lg / 2) + ux * cote * (off + pr / 2)
                    hx, hy = abs(ux) * lg / 2 + abs(uy) * pr / 2, abs(uy) * lg / 2 + abs(ux) * pr / 2
                    rect = [r2(cx - hx), r2(cy - hy), r2(cx + hx), r2(cy + hy)]
                    if libre(rect):
                        tons = ["#e8c9a0", "#ddb48f", "#efd9b8", "#d9a98a", "#e6c2a6", "#f0e0c0"] if not maison else ["#efe2c4", "#e6d3b3", "#f3e9d2", "#e9d8bf"]
                        batiments.append({"rect": rect, "h": r2((4.5 + 2 * h01(s, r["id"])) if maison else (12 + 8 * h01(s, cote, r["id"]))),
                                          "couleur": tons[int(h01(r["id"], cote, s) * len(tons))], "toit": maison})
                    s += lg + (5 if maison else 0.4 + 2 * h01(s, r["id"]))
    reperes = [{"nom": n, "x": x, "y": y} for lid, (z, x, y, n) in ENDROITS.items() if z == R["id"] and lid != "bureau-de-vote"]
    reperes += [{"nom": {"domicile-thomas": "chez Thomas", "appartement-vial": "chez les Vial", "epicerie-chazal": "l'épicerie",
                         "maison-chazal": "chez les Chazal", "maison-morel": "chez les Morel"}[k], "x": x, "y": y} for k, (z, x, y) in PORTES.items() if z == R["id"]]
    return {"id": R["id"], "nom": R["nom"], "adresse": R["adresse"], "type": "rue", "cadre": R["cadre"], "hauteur": 3, "pieces": [], "portes": [], "fenetres": [],
            "mobilier": [], "postes": {}, "rues": rues, "places": [], "batiments": batiments, "zones": zones, "reperes": reperes}


def centre(rect):
    return ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)


def endroit(lot, piece, posture, action, prenom, LIEUX):
    """(x, y, z, angle) : l'endroit précis du pas dans la pièce."""
    pc = next((p for p in lot["pieces"] if p["id"] == piece), None)
    if pc is None:
        return None
    cx, cy = centre(pc["rect"])
    meubles = [m for m in lot["mobilier"] if m["piece"] == piece]
    mot = next((l for t, l in LIEUX if action.startswith(t)), None)
    cible = None
    if mot:
        cands = [m for m in meubles if norm(mot) in norm(m["nom"])]
        cible = next((m for m in cands if norm(prenom) in norm(m["nom"])), cands[0] if cands else None)
    if mot and "fenetre" in norm(mot):   # à la fenêtre : devant la fenêtre de la pièce
        f = next((f for f in lot["fenetres"] if f["piece"] == piece), None)
        if f:
            (ax, ay), (bx, by) = f["segment"]
            fx, fy = (ax + bx) / 2, (ay + by) / 2
            d = math.hypot(cx - fx, cy - fy) or 1
            return [fx + (cx - fx) / d * 0.45, fy + (cy - fy) / d * 0.45, 0, math.atan2(fy - cy, fx - cx)]
    SIEGES = ("canape", "fauteuil", "lit", "chaise", "tabouret", "table", "etabli", "bureau", "comptoir", "cuvette", "banc")
    regard = None
    if cible is not None and posture == "assis" and not any(k in norm(cible["nom"]) for k in SIEGES):
        # assis devant quelque chose qui n'est pas un siège (la télévision) : dans son fauteuil, sinon sur le canapé, tourné vers elle
        x0, y0, x1, y1, _ = cible["boite"]
        regard = ((x0 + x1) / 2, (y0 + y1) / 2)
        perso = [m for m in meubles if "fauteuil" in norm(m["nom"]) and norm(prenom) in norm(m["nom"])]
        cible = perso[0] if perso else next((m for m in meubles if "canape" in norm(m["nom"])), None) or             next((m for m in meubles if any(k in norm(m["nom"]) for k in ("fauteuil", "chaise", "table"))), None)
        if cible is not None and not any(k in norm(cible["nom"]) for k in ("table",)):
            x0, y0, x1, y1, h = cible["boite"]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            return [mx, my, min(h, 0.45), math.atan2(regard[1] - my, regard[0] - mx)]
    if cible is None and posture == "allongé":
        cible = next((m for m in meubles if any(k in norm(m["nom"]) for k in ("lit", "canape"))), None)
    if cible is None and posture == "assis":
        perso = [m for m in meubles if "fauteuil" in norm(m["nom"]) and norm(prenom) in norm(m["nom"])]
        cible = perso[0] if perso else next((m for m in meubles if any(k in norm(m["nom"]) for k in ("table", "canape", "fauteuil", "tabouret", "chaise", "cuvette"))), None)
    if cible is None:
        postes = lot["postes"].get(piece, {})
        p = postes.get(posture) or postes.get("debout")
        if p:
            return [p[0], p[1], p[4] if len(p) > 4 and posture != "debout" else 0, math.atan2(p[3], p[2])]
        return [cx + (h01(prenom, piece) - 0.5) * 0.8, cy + (h01(piece, prenom) - 0.5) * 0.8, 0, 0]
    x0, y0, x1, y1, h = cible["boite"]
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nom = norm(cible["nom"])
    if posture == "allongé" and any(k in nom for k in ("lit", "canape")):
        long_x = (x1 - x0) >= (y1 - y0)
        return [mx, my, h, 0 if long_x else math.pi / 2]
    if posture == "assis" and not any(k in nom for k in ("table", "etabli", "bureau", "comptoir")):
        return [mx, my, min(h, 0.45), math.atan2(cy - my, cx - mx)]
    # debout devant le meuble (ou assis devant une table) : du côté du milieu de la pièce
    dx, dy = cx - mx, cy - my
    if abs(dx) * (y1 - y0) > abs(dy) * (x1 - x0):
        x, y = (x1 + 0.35 if dx > 0 else x0 - 0.35), min(max(cy, y0 + 0.2), y1 - 0.2)
    else:
        x, y = min(max(cx, x0 + 0.2), x1 - 0.2), (y1 + 0.35 if dy > 0 else y0 - 0.35)
    x0p, y0p, x1p, y1p = pc["rect"]
    x, y = min(max(x, x0p + 0.25), x1p - 0.25), min(max(y, y0p + 0.25), y1p - 0.25)
    return [x, y, 0.45 if posture == "assis" else 0, math.atan2(my - y, mx - x)]


def porte_entre(lot, a, b):
    for d in lot["portes"]:
        if set(d["entre"]) == {a, b}:
            (x0, y0), (x1, y1) = d["segment"]
            return [(x0 + x1) / 2, (y0 + y1) / 2]
    return None


def humeur(e):
    return max(-1.0, min(1.0, e.get("joie", 0.4) + 0.3 * e.get("fierte", 0.3) - e.get("tristesse", 0.2) - 0.6 * e.get("anxiete", 0.2)
                         - e.get("colere", 0.05) - 0.5 * e.get("solitude", 0.2) + 0.1))


# ------------------------------------------------------------------ export
def construire(quartier):
    """Les données de la vue pour les journées d'un dossier (le monde de référence, ou une partie)."""
    lots, ou = charger_plans()
    W = json.load(open(os.path.join(MONDE, "croix-rousse.json"), encoding="utf-8"))
    n_rue = {R["id"]: len(lots) + k for k, R in enumerate(RUES)}
    reseaux = {R["id"]: reseau(R, W) for R in RUES}
    lots += [batir(R, W) for R in RUES]
    LIEUX = actions_lieux()
    GESTE = actions_gestes()
    T = Textes()
    habitants = sorted(d for d in os.listdir(quartier) if os.path.isdir(os.path.join(quartier, d)))
    dates = sorted(f[:-5] for f in os.listdir(os.path.join(quartier, habitants[0])) if f.endswith(".json"))
    fiches = {p: charger(p) for p in habitants}
    noms_lieux = {}
    for f in fiches.values():
        for l in f.get("lieux", []):
            noms_lieux.setdefault(l["id"], l["nom"])
    journees = {p: [s for d in dates for s in json.load(open(os.path.join(quartier, p, d + ".json"), encoding="utf-8"))["pas"]] for p in habitants}
    N = len(journees[habitants[0]])
    pas = {p: [] for p in habitants}
    chemins = []
    precedent = {p: None for p in habitants}
    for i in range(N):
        places = {}
        for p in habitants:
            s = journees[p][i]
            ld = logement_de(p, s, fiches[p])
            loc = ou.get(ld) if ld else None
            if loc is None:
                places[p] = None
                continue
            n, niv = loc
            piece = f"{ld[0]}/{ld[1]}"
            e = endroit(lots[n], piece, s.get("posture", "debout"), s.get("action", ""), fiches[p]["identite"]["prenom"], LIEUX)
            places[p] = (n, niv, piece, e)
        # deux habitants au même endroit : le second se décale (de l'autre côté d'une table, ou à côté)
        vus = []
        for p in habitants:
            pl = places[p]
            if not pl or not pl[3]:
                continue
            for q, ql in vus:
                if ql[0] == pl[0] and ql[1] == pl[1] and math.dist(ql[3][:2], pl[3][:2]) < 0.45:
                    a = pl[3][3]
                    pl[3][0] += 0.6 * math.cos(a + math.pi / 2)
                    pl[3][1] += 0.6 * math.sin(a + math.pi / 2)
            vus.append((p, pl))
        for p in habitants:
            s, pl = journees[p][i], places[p]
            b = [round(s.get("besoins", {}).get(k, 0)) for k in BESOINS]
            mood = round(humeur(s.get("emotions", {})), 2)
            textes = [T(s.get("activite", "")), T(s.get("action", "")), T(s.get("pensee") or "")]
            geste = next((c for tx, c in GESTE if s.get("action", "").startswith(tx)), 0)
            if not pl or not pl[3]:
                dehors = noms_lieux.get(s.get("lieu"), s.get("lieu", "dehors"))
                if s.get("lieu") == "exterieur":
                    dehors = noms_lieux.get(s["piece"], s["piece"].replace("-", " "))
                pas[p].append([-1, 0, 0, 0, 0, 0, POSES.get(s.get("posture"), 0)] + textes + [mood] + b + [-1, T(dehors), int("phase_sommeil" in s), geste])
                precedent[p] = None
                continue
            n, niv, piece, (x, y, z, ang) = pl
            # le chemin depuis le pas précédent, porte par porte
            ch = (s.get("deplacement") or {}).get("chemin") or []
            ch_id = -1
            prev = precedent[p]
            if ch and prev and prev[0] == n:
                logement = piece.split("/")[0]
                ids = [f"{logement}/{c.split(':')[-1]}" for c in ch]
                pts = [[r2(prev[2]), r2(prev[3]), prev[1]]]
                for a, bb in zip(ids, ids[1:]):
                    d = porte_entre(lots[n], a, bb)
                    if d:
                        nb = next((pc["niveau"] for pc in lots[n]["pieces"] if pc["id"] == bb), niv)
                        pts.append([r2(d[0]), r2(d[1]), nb])
                pts.append([r2(x), r2(y), niv])
                if len(pts) > 2 or math.dist(pts[0][:2], pts[-1][:2]) > 0.3:
                    chemins.append(pts)
                    ch_id = len(chemins) - 1
            pieces_ids = [pc["id"] for pc in lots[n]["pieces"]]
            pas[p].append([n, niv, r2(x), r2(y), r2(z), round(ang, 2), POSES.get(s.get("posture"), 0)] + textes + [mood] + b
                          + [ch_id, pieces_ids.index(piece), int("phase_sommeil" in s or s.get("mode") == "sommeil"), geste])
            precedent[p] = (n, niv, x, y)
    # dehors : à un endroit connu, ou en chemin entre deux (sa porte, un endroit connu), sur le terrain de rue
    def ancre(p, i):
        """L'endroit (terrain de rue, x, y) où il est au pas i, s'il est à un endroit connu ou chez lui ; None sinon."""
        if i < 0 or i >= N:
            return None
        s, r = journees[p][i], pas[p][i]
        if r[0] >= 0 and lots[r[0]].get("type") != "rue":
            logement = lots[r[0]]["pieces"][r[-3]]["id"].split("/")[0]
            return PORTES.get(logement)
        cle = s.get("piece") if s.get("lieu") == "exterieur" else s.get("lieu")
        if cle in ENDROITS:
            z, x, y, _ = ENDROITS[cle]
            return (z, x + (h01(p, cle) - 0.5) * 6, y + (h01(cle, p) - 0.5) * 4)
        return None
    for p in habitants:
        J = journees[p]
        for i in range(N):
            s, r = J[i], pas[p][i]
            if r[0] >= 0:
                continue
            cle = s.get("piece") if s.get("lieu") == "exterieur" else s.get("lieu")
            if s.get("lieu") in VEHICULES or s.get("posture") == "assis" and s.get("lieu") == "trajet-transports":
                continue
            a = ancre(p, i)
            if a is None and (cle in TRAJETS or s.get("lieu") in TRAJETS):
                # en chemin : entre l'endroit d'avant et celui d'après la suite des pas de trajet
                d, f = i, i
                while d - 1 >= 0 and pas[p][d - 1][0] < 0 and ancre(p, d - 1) is None and (J[d - 1].get("lieu") in TRAJETS or J[d - 1].get("piece") in TRAJETS):
                    d -= 1
                while f + 1 < N and pas[p][f + 1][0] < 0 and ancre(p, f + 1) is None and (J[f + 1].get("lieu") in TRAJETS or J[f + 1].get("piece") in TRAJETS):
                    f += 1
                A, B = ancre(p, d - 1), ancre(p, f + 1)
                if A and B and A[0] == B[0]:
                    u = (i - d + 1) / (f - d + 2)
                    x, y, ang = le_long(itineraire(reseaux[A[0]], (A[1], A[2]), (B[1], B[2])), u)
                    a = (A[0], x, y)
                    r[5] = round(ang, 2)
                    r[6] = 3
                elif A or B:
                    a = A or B
            if a is None:
                continue
            r[0], r[1], r[2], r[3], r[4] = n_rue[a[0]], 0, r2(a[1]), r2(a[2]), 0
    # lumières : pièces éclairées à chaque pas, par terrain (les « lumiere-<pièce> » des appareils allumés de chacun)
    lumieres = [[] for _ in range(N)]
    for p in habitants:
        for i, s in enumerate(journees[p]):
            r = pas[p][i]
            if r[0] < 0 or lots[r[0]].get("type") == "rue":
                continue
            logement = lots[r[0]]["pieces"][r[-3]]["id"].split("/")[0]
            for a in s.get("appareils_allumes", []):
                if a.startswith("lumiere-"):
                    pid = f"{logement}/{a[8:].split(':')[-1]}"
                    k = next((j for j, pc in enumerate(lots[r[0]]["pieces"]) if pc["id"] == pid), None)
                    if k is not None and [r[0], k] not in lumieres[i]:
                        lumieres[i].append([r[0], k])
    eph = fiches[habitants[0]]["meta"]["ephemerides_lyon_approximatives"]
    D = {"dates": dates, "pas_par_jour": 288, "besoins": BESOINS, "lots": lots,
         "habitants": [{"id": p, "prenom": fiches[p]["identite"]["prenom"], "nom": fiches[p]["identite"]["nom"], "genre": fiches[p]["identite"].get("genre", "homme"),
                        "age": fiches[p]["identite"].get("age"), "couleur": COULEURS.get(p, "#888888")} for p in habitants],
         "champs": ["lot", "niveau", "x", "y", "z", "angle", "pose", "activite", "action", "pensee", "humeur"] + BESOINS + ["chemin", "piece", "dort", "geste"],
         "pas": pas, "chemins": chemins, "lumieres": lumieres, "textes": T.liste,
         "soleil": {d: [eph[d]["lever_soleil"], eph[d]["coucher_soleil"]] for d in dates if d in eph}}
    return D


def exporter(quartier, sortie):
    D = construire(quartier)
    t = "// Généré par outils/exporter_sims.py — ne pas modifier à la main.\nwindow.SIMS = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";\n"
    open(sortie, "w", encoding="utf-8").write(t)
    N = len(next(iter(D["pas"].values())))
    print(f"{len(D['habitants'])} habitants, {len(D['lots'])} terrains, {N} pas, {len(D['chemins'])} chemins, {len(D['textes'])} textes → {os.path.relpath(sortie, RACINE)} ({len(t) // 1024} Ko)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quartier", default=os.path.join(RACINE, "data", "quartier"))
    ap.add_argument("--sortie", default=os.path.join(RACINE, "vue", "sims.js"))
    a = ap.parse_args()
    exporter(a.quartier, a.sortie)


if __name__ == "__main__":
    main()
