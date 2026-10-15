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
- les pièces éclairées.
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
    LIEUX = actions_lieux()
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
            if not pl or not pl[3]:
                dehors = noms_lieux.get(s.get("lieu"), s.get("lieu", "dehors"))
                if s.get("lieu") == "exterieur":
                    dehors = noms_lieux.get(s["piece"], s["piece"].replace("-", " "))
                pas[p].append([-1, 0, 0, 0, 0, 0, POSES.get(s.get("posture"), 0)] + textes + [mood] + b + [-1, T(dehors), s["mode"] == "sommeil" if "mode" in s else int("phase_sommeil" in s)])
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
                          + [ch_id, pieces_ids.index(piece), int("phase_sommeil" in s or s.get("mode") == "sommeil")])
            precedent[p] = (n, niv, x, y)
    # lumières : pièces éclairées à chaque pas, par terrain (les « lumiere-<pièce> » des appareils allumés de chacun)
    lumieres = [[] for _ in range(N)]
    for p in habitants:
        for i, s in enumerate(journees[p]):
            r = pas[p][i]
            if r[0] < 0:
                continue
            logement = lots[r[0]]["pieces"][r[-2]]["id"].split("/")[0]
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
         "champs": ["lot", "niveau", "x", "y", "z", "angle", "pose", "activite", "action", "pensee", "humeur"] + BESOINS + ["chemin", "piece", "dort"],
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
