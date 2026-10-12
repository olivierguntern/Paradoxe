"""Prépare les données de la vue fil de fer (vue/donnees.js).

Usage : python3 outils/exporter_vue.py [--personnage thomas-berthier] [--monde data/monde/croix-rousse.json]

Lit la fiche du personnage, la géométrie du monde et toutes les journées de
data/timelines/<personnage>/, puis calcule pour chaque pas :
- le trajet de Thomas dans l'immeuble (portes franchies, escalier, allée) ;
- son trajet sur le parcours de course quand il est dehors ;
- sa pose (debout, assis, allongé, en course, en marche) ;
- la position en 3D de chaque emplacement d'objet.

Contrôles : chaque liaison du plan de la fiche doit avoir une porte, chaque
pièce un rectangle, chaque emplacement d'objet un point. Les distances entre
pièces mesurées sur le plan sont comparées à celles de la fiche.
"""
import argparse
import glob
import json
import math
import os
import sys
from collections import deque

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BESOINS = ["faim", "soif", "energie", "hygiene", "toilettes", "social", "detente"]
EMOTIONS = ["joie", "tristesse", "anxiete", "colere", "solitude", "fierte", "excitation", "concentration"]
POSES = {"debout": "debout", "assis": "assis", "allongé": "allonge", "en course": "course", "en marche": "marche"}
APPROCHE = 0.45  # distance du point de passage devant une porte (m)


def dist(a, b):
    return math.dist(a[:2], b[:2])


def centre(r):
    return [(r[0] + r[2]) / 2, (r[1] + r[3]) / 2]


def longueur(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def point_a(pts, s):
    """Point d'une polyligne à l'abscisse curviligne s."""
    cumul = 0.0
    for p, q in zip(pts, pts[1:]):
        l = math.dist(p, q)
        if cumul + l >= s:
            u = 0.0 if l == 0 else max(0.0, (s - cumul) / l)
            return [p[i] + (q[i] - p[i]) * u for i in range(3)]
        cumul += l
    return list(pts[-1])


def sous_chemin(pts, a, b):
    """Points d'une polyligne entre les abscisses curvilignes a et b (b peut être avant a)."""
    lo, hi = min(a, b), max(a, b)
    out, cumul = [point_a(pts, lo)], 0.0
    for p, q in zip(pts, pts[1:]):
        cumul += math.dist(p, q)
        if lo < cumul < hi:
            out.append(list(q))
    out.append(point_a(pts, hi))
    out = [[round(v, 1) for v in p] for p in out]
    return out[::-1] if b < a else out


class Monde:
    def __init__(self, fiche, geo):
        self.fiche, self.geo = fiche, geo
        self.im = geo["immeuble"]
        self.lg = geo["logement"]
        self.H = self.im["hauteur_etage"]
        self.Z = self.im["etage_logement"] * self.H
        self.pieces = self.lg["pieces"]
        self.portes = {}
        for p in self.lg["portes"]:
            a, b = p["entre"]
            m = [(p["segment"][0][0] + p["segment"][1][0]) / 2, (p["segment"][0][1] + p["segment"][1][1]) / 2]
            self.portes[(a, b)] = self.portes[(b, a)] = {"milieu": m, "segment": p["segment"]}
        self.voisins = {}
        for a, b in self.portes:
            self.voisins.setdefault(a, set()).add(b)

    # ---------------------------------------------------------------- points
    def a3(self, p, z=0.0):
        """Point du logement vers le repère de l'immeuble."""
        return [round(p[0], 2), round(p[1], 2), round(self.Z + z, 2)]

    def approche(self, piece, porte):
        """Point situé devant la porte, à l'intérieur de la pièce."""
        (x0, y0), (x1, y1) = porte["segment"]
        m = porte["milieu"]
        if y0 == y1:
            c = centre(self.pieces[piece])
            s = 1 if c[1] > y0 else -1
            return [m[0], m[1] + s * APPROCHE]
        c = centre(self.pieces[piece])
        s = 1 if c[0] > x0 else -1
        return [m[0] + s * APPROCHE, m[1]]

    def poste(self, piece, posture, activite):
        P = self.lg["postes"].get(piece)
        if not P:
            return centre(self.pieces[piece]) + [0.0, 1.0]
        if posture == "allongé" and "allongé" in P:
            return P["allongé"]
        if posture == "assis":
            if piece == "sejour" and any(k in activite for k in self.lg["activites_a_table"]):
                return P["assis_a_table"]
            if "assis" in P:
                return P["assis"]
        if piece == "salle-de-bain" and "ouche" in activite:
            return P["douche"]
        return P["debout"]

    # ---------------------------------------------------------------- chemins
    def chemin_pieces(self, a, b):
        if a == b:
            return [a]
        vu, file = {a: None}, deque([a])
        while file:
            x = file.popleft()
            for y in sorted(self.voisins.get(x, ())):
                if y not in vu:
                    vu[y] = x
                    file.append(y)
        if b not in vu:
            return [a, b]
        out = [b]
        while out[-1] != a:
            out.append(vu[out[-1]])
        return out[::-1]

    def traversee(self, pieces):
        """Points de passage (logement) pour une suite de pièces voisines."""
        pts = []
        for a, b in zip(pieces, pieces[1:]):
            if a == b:
                continue
            porte = self.portes.get((a, b))
            if not porte:
                pts.append(centre(self.pieces[b]))
                continue
            pts += [self.approche(a, porte), porte["milieu"], self.approche(b, porte)]
        return pts

    def escalier(self, sens):
        """Points de l'escalier entre le palier du logement et la rue (descente) ou l'inverse."""
        E, H = self.im["escalier"], self.H
        xa = sum(E["volee_montante"]["x"]) / 2
        xd = sum(E["volee_descendante"]["x"]) / 2
        y0, y1 = E["volee_montante"]["y"]
        ym = (E["palier_intermediaire"][1] + E["palier_intermediaire"][3]) / 2
        pts = []
        for k in range(self.im["etage_logement"], 0, -1):
            z = k * H
            pts += [[xd, y0, z], [xd, y1, z - H / 2], [(xa + xd) / 2, ym, z - H / 2], [xa, y1, z - H / 2], [xa, y0, z - H]]
        porte = self.im["porte_immeuble"]
        xp = (porte[0][0] + porte[1][0]) / 2
        pts += [[xp, 5.0, 0.0], [xp, 0.0, 0.0], [xp, self.im["rue"]["trottoir"] + 0.6, 0.0]]
        pts = [[round(v, 2) for v in p] for p in pts]
        return pts if sens == "descente" else pts[::-1]

    def detour_poubelles(self):
        lp = self.im["local_poubelles"]
        E = self.im["escalier"]
        xa = sum(E["volee_montante"]["x"]) / 2
        return [[xa + 1.2, 6.8, 0.0], [lp[0] + 1.0, 6.8, 0.0], [lp[0] + 1.0, lp[1] + 0.6, 0.0], [lp[0] + 1.0, 6.8, 0.0]]

    # ---------------------------------------------------------------- murs
    def murs(self):
        lignes = {}
        for pid, (x0, y0, x1, y1) in self.pieces.items():
            if pid == "palier":
                continue
            for cle, a, b in ((("h", y0), x0, x1), (("h", y1), x0, x1), (("v", x0), y0, y1), (("v", x1), y0, y1)):
                lignes.setdefault(cle, []).append([a, b])
        ouvertures = {}
        for p in self.lg["portes"]:
            (x0, y0), (x1, y1) = p["segment"]
            if y0 == y1:
                ouvertures.setdefault(("h", y0), []).append(sorted([x0, x1]))
            else:
                ouvertures.setdefault(("v", x0), []).append(sorted([y0, y1]))
        out = []
        for (sens, c), ivs in lignes.items():
            ivs.sort()
            fus = []
            for a, b in ivs:
                if fus and a <= fus[-1][1] + 1e-9:
                    fus[-1][1] = max(fus[-1][1], b)
                else:
                    fus.append([a, b])
            for a, b in fus:
                morceaux = [[a, b]]
                for oa, ob in ouvertures.get((sens, c), []):
                    nouveaux = []
                    for ma, mb in morceaux:
                        if ob <= ma or oa >= mb:
                            nouveaux.append([ma, mb])
                            continue
                        if oa > ma:
                            nouveaux.append([ma, oa])
                        if ob < mb:
                            nouveaux.append([ob, mb])
                    morceaux = nouveaux
                for ma, mb in morceaux:
                    out.append([[ma, c], [mb, c]] if sens == "h" else [[c, ma], [c, mb]])
        return [[[round(v, 2) for v in p] for p in s] for s in out]

    # ---------------------------------------------------------------- emplacements d'objets
    def emplacement(self, texte):
        S = self.lg["supports"]
        if any(texte.startswith(k) for k in S["porte_par_thomas"]):
            return {"porte": True}
        if "local poubelles" in texte:
            lp = self.im["local_poubelles"]
            return {"p": [lp[0] + 1.0, lp[1] + 1.0, 0.3], "piece": "local-poubelles"}
        if " / " in texte:
            piece, reste = texte.split(" / ", 1)
            for motif, pt in S.get(piece, []):
                if motif in reste:
                    return {"p": self.a3(pt[:2], pt[2]), "piece": piece}
            if piece in self.pieces:
                return {"p": self.a3(centre(self.pieces[piece]), 0.0), "piece": piece, "approche": True}
        for motif, piece, pt in S["sans_piece"]:
            if motif in texte:
                return {"p": self.a3(pt[:2], pt[2]), "piece": piece}
        return None

    def distances_plan(self):
        """Distance centre à centre par la porte, pour chaque liaison de la fiche."""
        out = []
        for l in self.fiche["domicile"]["plan"]["liaisons"]:
            a, b = l["a"], l["b"]
            porte = self.portes.get((a, b))
            if not porte:
                out.append((a, b, l["distance_m"], None))
                continue
            ca = self.lg["postes"]["palier"]["debout"][:2] if a == "palier" else centre(self.pieces[a])
            cb = centre(self.pieces[b])
            out.append((a, b, l["distance_m"], round(dist(ca, porte["milieu"]) + dist(porte["milieu"], cb), 1)))
        return out


# -------------------------------------------------------------------- parcours extérieur
def trajets_exterieurs(pas, Q):
    """Points du parcours (repère du quartier) pour chaque pas passé dehors."""
    desc, quai = Q["descente"], Q["quai"]
    L_desc, L_quai = longueur(desc), longueur(quai)
    ext = [k for k, s in enumerate(pas) if s["lieu"] == "exterieur"]
    out = {}
    if not ext:
        return out
    phases, vu_quai = [], False
    for k in ext:
        if "quais" in pas[k]["piece"]:
            vu_quai = True
            phases.append("quai")
        else:
            phases.append("montee" if vu_quai else "descente")
    d = {k: sum(p["distance_m"] for p in pas[k].get("deplacement", {}).get("parcours", [])) for k in ext}
    total = {ph: sum(d[k] for k, f in zip(ext, phases) if f == ph) or 1 for ph in ("descente", "quai", "montee")}
    if total["quai"] / 2 > L_quai:
        raise SystemExit(f"Le quai dessiné ({round(L_quai)} m) est plus court que l'aller ({total['quai'] / 2} m).")
    cumul = {"descente": 0.0, "quai": 0.0, "montee": 0.0}
    for k, ph in zip(ext, phases):
        c0, c1 = cumul[ph], cumul[ph] + d[k]
        cumul[ph] = c1
        if ph == "descente":
            pts = sous_chemin(desc, c0 / total[ph] * L_desc, c1 / total[ph] * L_desc)
        elif ph == "montee":
            pts = sous_chemin(desc, (1 - c0 / total[ph]) * L_desc, (1 - c1 / total[ph]) * L_desc)
        else:
            demi = total[ph] / 2
            a0 = c0 if c0 <= demi else total[ph] - c0
            a1 = c1 if c1 <= demi else total[ph] - c1
            if c0 < demi < c1:
                pts = sous_chemin(quai, a0, demi) + sous_chemin(quai, demi, a1)[1:]
            else:
                pts = sous_chemin(quai, a0, a1)
        out[k] = {"pts": pts, "phase": ph}
    return out


# -------------------------------------------------------------------- export
def exporter(perso, chemin_monde, sortie):
    fiche = json.load(open(os.path.join(RACINE, "data", "personnages", f"{perso}.json"), encoding="utf-8"))
    geo = json.load(open(chemin_monde, encoding="utf-8"))
    M = Monde(fiche, geo)
    erreurs, avertissements = [], []

    # contrôles du plan
    for p in fiche["domicile"]["pieces"]:
        if p["id"] not in M.pieces:
            erreurs.append(f"pièce sans rectangle : {p['id']}")
        else:
            x0, y0, x1, y1 = M.pieces[p["id"]]
            surf = round((x1 - x0) * (y1 - y0), 2)
            if abs(surf - p["surface_m2"]) > 0.05:
                avertissements.append(f"{p['id']} : {surf} m² sur le plan, {p['surface_m2']} m² dans la fiche")
    for l in fiche["domicile"]["plan"]["liaisons"]:
        if (l["a"], l["b"]) not in M.portes:
            erreurs.append(f"liaison sans porte : {l['a']} – {l['b']}")

    fichiers = sorted(glob.glob(os.path.join(RACINE, "data", "timelines", perso, "*.json")))
    jours, emplacements, noms = [], {}, {o["id"]: o["nom"] for o in fiche["objets"]}
    precedent, hors = None, False

    def note_emplacement(t):
        if t not in emplacements:
            e = M.emplacement(t)
            if e is None:
                avertissements.append(f"emplacement inconnu : « {t} »")
                e = {"p": M.a3(centre(M.pieces["sejour"]), 0.0), "piece": "sejour", "approche": True}
            if e.get("approche"):
                avertissements.append(f"emplacement placé au centre de la pièce : « {t} »")
            emplacements[t] = e

    for fn in fichiers:
        J = json.load(open(fn, encoding="utf-8"))
        pas = J["pas"]
        for t in J["etat_initial"]["positions"].values():
            note_emplacement(t)
        exterieur = trajets_exterieurs(pas, geo["quartier"])
        if precedent is None:
            p0 = M.poste(J["etat_initial"]["piece"], "allongé", "")
            precedent = {"pt": M.a3(p0[:2], p0[4] if len(p0) > 4 else 0), "piece": J["etat_initial"]["piece"]}
        sortie_pas = []
        for k, s in enumerate(pas):
            dep = s.get("deplacement", {})
            esc = dep.get("escalier", {}).get("sens")
            chemin = dep.get("chemin") or []
            poubelles = any("local poubelles" in o["vers"] for o in s.get("objets", []))
            w = None
            if s["lieu"] == "domicile":
                po = M.poste(s["piece"], s["posture"], s["activite"])
                cible = M.a3(po[:2], 0.0)
                if esc == "montee":
                    pieces = chemin if chemin else ["palier", s["piece"]]
                    w = M.escalier("montee") + [M.a3(p) for p in M.traversee(pieces)] + [cible]
                else:
                    depart = precedent["piece"]
                    pieces = chemin if chemin else M.chemin_pieces(depart, s["piece"])
                    if pieces and pieces[0] != depart and not hors:
                        pieces = M.chemin_pieces(depart, pieces[0]) + pieces[1:]
                    w = [precedent["pt"]] + [M.a3(p) for p in M.traversee(pieces)] + [cible]
                hors = False
                precedent = {"pt": cible, "piece": s["piece"]}
            else:
                if esc == "descente":
                    pieces = chemin if chemin else [precedent["piece"], "palier"]
                    if pieces[0] != precedent["piece"]:
                        pieces = M.chemin_pieces(precedent["piece"], pieces[0]) + pieces[1:]
                    pal = M.lg["postes"]["palier"]["debout"]
                    descente = M.escalier("descente")
                    if poubelles:
                        descente = descente[:-3] + M.detour_poubelles() + descente[-3:]
                    w = [precedent["pt"]] + [M.a3(p) for p in M.traversee(pieces)] + [M.a3(pal[:2])] + descente
                    precedent = {"pt": descente[-1], "piece": "palier"}
                hors = True
            # suppression des points répétés
            if w:
                propre = [w[0]]
                for p in w[1:]:
                    if math.dist(p, propre[-1]) > 0.01:
                        propre.append(p)
                w = propre
            pose = POSES.get(s["posture"], "debout")
            d = None
            if s["lieu"] == "domicile":
                po = M.poste(s["piece"], s["posture"], s["activite"])
                d = [po[2], po[3], po[4] if len(po) > 4 else 0.0] if len(po) > 3 else [0.0, 1.0, 0.0]
            for o in s.get("objets", []):
                note_emplacement(o["de"])
                note_emplacement(o["vers"])
            nouveaux = []
            for o in s.get("nouveaux_objets", []):
                noms[o["id"]] = o["nom"]
                note_emplacement(o["position"])
                nouveaux.append([o["id"], o["position"]])
            e = {
                "h": s["heure"], "pc": s["piece"], "l": "d" if s["lieu"] == "domicile" else "e",
                "po": pose, "a": s["activite"], "x": s["action"],
                "b": [round(s["besoins"][n], 1) for n in BESOINS],
                "em": [round(s["emotions"][n], 3) for n in EMOTIONS],
                "ap": s.get("appareils_allumes", []),
            }
            if s.get("pensee"):
                e["pe"] = s["pensee"]
            if s.get("reve"):
                e["r"] = s["reve"]
            if s.get("phase_sommeil"):
                e["ps"] = s["phase_sommeil"]
            if s.get("evenements"):
                e["ev"] = [v["id"] for v in s["evenements"]]
            if s.get("objets"):
                e["ob"] = [[o["objet"], o["de"], o["vers"]] for o in s["objets"]]
            if nouveaux:
                e["no"] = nouveaux
            if s.get("consommation"):
                e["co"] = [[c.get("produit"), c.get("quantite")] for c in s["consommation"] if isinstance(c, dict)]
            if w and len(w) > 1:
                e["w"] = w
            if esc:
                e["esc"] = esc
            if d:
                e["d"] = [round(v, 2) for v in d]
            if hors:
                e["hors"] = 1
            if k in exterieur:
                e["q"] = exterieur[k]["pts"]
                e["qp"] = exterieur[k]["phase"]
            sortie_pas.append(e)
        eph = fiche["meta"]["ephemerides_lyon_approximatives"].get(J["meta"]["date"], {})
        jours.append({
            "date": J["meta"]["date"], "jour": J["meta"]["jour"],
            "methode": "agent" if any("agent autonome" in m for m in J["meta"].get("methode", [])) else "reference",
            "lever": eph.get("lever_soleil"), "coucher": eph.get("coucher_soleil"),
            "positions": J["etat_initial"]["positions"],
            "pas": sortie_pas,
        })

    # point de départ de Thomas le premier jour
    p0 = M.poste(json.load(open(fichiers[0], encoding="utf-8"))["etat_initial"]["piece"], "allongé", "")
    donnees = {
        "personnage": {"id": perso, "nom": f"{fiche['identite']['prenom']} {fiche['identite']['nom']}"},
        "monde": {
            "immeuble": geo["immeuble"], "logement": {k: geo["logement"][k] for k in ("pieces", "portes", "fenetres", "mobilier")},
            "murs": M.murs(), "z_logement": M.Z, "appareils": geo["logement"]["appareils"],
            "quartier": geo["quartier"], "statut": geo["meta"]["statut"],
        },
        "noms_pieces": {p["id"]: p["nom"] for p in fiche["domicile"]["pieces"]} | {"palier": "Palier", "quais de Saône": "Quais de Saône",
                                                                              "pentes de la Croix-Rousse": "Pentes de la Croix-Rousse"},
        "objets": noms,
        "emplacements": emplacements,
        "evenements": {k: v["description"] for k, v in fiche["modele_emotionnel"]["evenements"].items()},
        "besoins": [{"id": n, "seuil": fiche["besoins"][n]["seuil_alerte"]} for n in BESOINS],
        "emotions": EMOTIONS,
        "depart": M.a3(p0[:2], 0.0),
        "jours": jours,
    }
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    with open(sortie, "w", encoding="utf-8") as f:
        f.write("window.PARADOXE = ")
        json.dump(donnees, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    print(f"{len(jours)} journées, {sum(len(j['pas']) for j in jours)} pas, {len(emplacements)} emplacements d'objets → {os.path.relpath(sortie, RACINE)}")
    print("Distances entre pièces (fiche / plan) :")
    for a, b, f_, p_ in M.distances_plan():
        print(f"  {a:>13} – {b:<13} {f_:>4} m / {p_} m")
    for a in avertissements:
        print("  ! " + a)
    if erreurs:
        for e in erreurs:
            print("ERREUR : " + e)
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--personnage", default="thomas-berthier")
    ap.add_argument("--monde", default=os.path.join(RACINE, "data", "monde", "croix-rousse.json"))
    ap.add_argument("--sortie", default=os.path.join(RACINE, "vue", "donnees.js"))
    a = ap.parse_args()
    exporter(a.personnage, a.monde, a.sortie)
