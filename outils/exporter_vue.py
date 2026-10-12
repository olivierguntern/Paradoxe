"""Prépare les données de la vue fil de fer (vue/donnees.js).

Usage : python3 outils/exporter_vue.py [--monde data/monde/croix-rousse.json]

Lit la géométrie du monde, les fiches des personnages qui y ont un logement et
toutes leurs journées (data/timelines/<personnage>/). Tout est exprimé dans un
seul repère (mètres) : x vers l'est, y vers le nord, z vers le haut.

Pour chaque pas de chaque personnage, l'export calcule :
- le trajet, porte par porte dans son logement, par les escaliers, puis dans
  les rues (courses à l'épicerie, parcours de course) ;
- sa pose (debout, assis, allongé, en marche, en course) et sa direction ;
- la position en 3D de chaque emplacement d'objet.

Il génère aussi, de façon déterministe, les immeubles ordinaires le long des
rues, les arbres du boulevard et des quais.

Contrôles : chaque liaison du plan d'une fiche doit avoir une porte, chaque
pièce un rectangle, chaque emplacement d'objet un point. Les distances entre
pièces mesurées sur le plan sont comparées à celles de la fiche.
"""
import argparse
import glob
import json
import math
import os
import sys
import zlib
from collections import deque

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BESOINS = ["faim", "soif", "energie", "hygiene", "toilettes", "social", "detente"]
EMOTIONS = ["joie", "tristesse", "anxiete", "colere", "solitude", "fierte", "excitation", "concentration"]
POSES = {"debout": "debout", "assis": "assis", "allongé": "allonge", "en course": "course", "en marche": "marche"}
APPROCHE = 0.45


def r2(v):
    return round(v, 2) + 0.0


def h01(*cle):
    return (zlib.crc32("|".join(map(str, cle)).encode()) % 10000) / 10000


def longueur(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def point_a(pts, s):
    cumul = 0.0
    for p, q in zip(pts, pts[1:]):
        l = math.dist(p, q)
        if cumul + l >= s:
            u = 0.0 if l == 0 else max(0.0, (s - cumul) / l)
            return [p[i] + (q[i] - p[i]) * u for i in range(len(p))]
        cumul += l
    return list(pts[-1])


def sous_chemin(pts, a, b):
    lo, hi = min(a, b), max(a, b)
    out, cumul = [point_a(pts, lo)], 0.0
    for p, q in zip(pts, pts[1:]):
        cumul += math.dist(p, q)
        if lo < cumul < hi:
            out.append(list(q))
    out.append(point_a(pts, hi))
    out = [[r2(v) for v in p] for p in out]
    return out[::-1] if b < a else out


class Repere:
    """Passage du repère local d'un bâtiment au repère du monde (rotations par quarts de tour)."""

    def __init__(self, origine, rotation):
        self.o, self.r = origine, rotation % 360

    def p(self, x, y):
        ox, oy = self.o
        return {0: (ox + x, oy + y), 270: (ox + y, oy - x), 90: (ox - y, oy + x), 180: (ox - x, oy - y)}[self.r]

    def v(self, dx, dy):
        return {0: (dx, dy), 270: (dy, -dx), 90: (-dy, dx), 180: (-dx, -dy)}[self.r]

    def rect(self, r):
        a, b = self.p(r[0], r[1]), self.p(r[2], r[3])
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]


class Terrain:
    def __init__(self, T):
        self.T = T

    def z(self, x, y):
        T = self.T
        fx = min(1.0, max(0.0, (T["bord_ouest_x"] - x) / T["largeur_pente_ouest"]))
        fy = min(1.0, max(0.0, (T["bord_sud_y"] - y) / T["largeur_pente_sud"]))
        fe = min(1.0, max(0.0, (x - T["bord_est_x"]) / T["largeur_pente_est"])) if "bord_est_x" in T else 0.0
        z = T["z_bas"] * max(fx, fy, fe)
        C = T.get("colline")
        if C:
            d2 = (x - C["centre"][0]) ** 2 + (y - C["centre"][1]) ** 2
            z += C["hauteur"] * math.exp(-d2 / (2 * C["sigma"] ** 2))
        return z

    def p3(self, pts):
        return [[r2(x), r2(y), r2(self.z(x, y))] for x, y in pts]


class Logement:
    def __init__(self, L, bat, fiche, z0=0.0):
        self.L, self.bat, self.fiche = L, bat, fiche
        self.R = Repere(bat["origine"], bat["rotation"])
        self.H = bat["hauteur_etage"]
        self.z0 = z0  # altitude du terrain au pied du bâtiment
        self.base = L["niveau"]
        self.pieces = L["pieces"]
        self.portes, self.voisins = {}, {}
        for p in L["portes"]:
            a, b = p["entre"]
            if p.get("escalier"):
                e = {"escalier": True}
            else:
                (x0, y0), (x1, y1) = p["segment"]
                e = {"milieu": [(x0 + x1) / 2, (y0 + y1) / 2], "segment": p["segment"]}
            self.portes[(a, b)] = self.portes[(b, a)] = e
            self.voisins.setdefault(a, set()).add(b)
            self.voisins.setdefault(b, set()).add(a)

    def niveau(self, piece):
        return self.base + self.pieces.get(piece, {}).get("niveau", 0)

    def pt(self, piece, xy, dz=0.0):
        x, y = self.R.p(*xy)
        return [r2(x), r2(y), r2(self.z0 + self.niveau(piece) * self.H + dz)]

    def centre(self, piece):
        r = self.pieces[piece]["rect"]
        return [(r[0] + r[2]) / 2, (r[1] + r[3]) / 2]

    def approche(self, piece, porte):
        (x0, y0), (x1, y1) = porte["segment"]
        m, c = porte["milieu"], self.centre(piece)
        if y0 == y1:
            return [m[0], m[1] + (APPROCHE if c[1] > y0 else -APPROCHE)]
        return [m[0] + (APPROCHE if c[0] > x0 else -APPROCHE), m[1]]

    def poste(self, piece, posture, activite):
        """Point, direction et hauteur de siège dans le repère du monde."""
        P = self.L["postes"].get(piece)
        if not P:
            po = self.centre(piece) + [0.0, 1.0]
        elif posture == "allongé" and "allongé" in P:
            po = P["allongé"]
        elif posture == "assis" and piece == "sejour" and "assis_a_table" in P and any(k in activite for k in self.L.get("activites_a_table", [])):
            po = P["assis_a_table"]
        elif posture == "assis" and "assis" in P:
            po = P["assis"]
        elif "ouche" in activite and "douche" in P:
            po = P["douche"]
        else:
            po = P.get("debout") or next(iter(v for k, v in P.items() if k != "principe"))
        d = self.R.v(po[2], po[3]) if len(po) > 3 else (0.0, 1.0)
        return self.pt(piece, po[:2]), [r2(d[0]), r2(d[1]), po[4] if len(po) > 4 else 0.0]

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

    def escalier_pts(self, de, vers):
        E = self.bat["escalier"]
        bas = self.R.p(*E["bas"])
        haut = self.R.p(*E["haut"])
        zb, zh = self.z0 + (self.base + E["depuis_niveau"]) * self.H, self.z0 + (self.base + E["jusqua_niveau"]) * self.H
        pts = [[r2(bas[0]), r2(bas[1]), r2(zb)], [r2(haut[0]), r2(haut[1]), r2(zh)]]
        return pts if self.niveau(de) <= self.niveau(vers) else pts[::-1]

    def traversee(self, pieces):
        pts = []
        for a, b in zip(pieces, pieces[1:]):
            if a == b:
                continue
            porte = self.portes.get((a, b))
            if not porte:
                pts.append(self.pt(b, self.centre(b)))
            elif porte.get("escalier"):
                pts += self.escalier_pts(a, b)
            else:
                pts += [self.pt(a, self.approche(a, porte)), self.pt(a, porte["milieu"]), self.pt(b, self.approche(b, porte))]
        return pts

    # ---------------------------------------------------------------- dessin
    def dessin(self, coupe=1.1):
        """Sols, murs coupés, portes, fenêtres et mobilier dans le repère du monde."""
        sols, murs, cadres, vitres, meubles, noms = [], [], [], [], [], []
        par_niveau = {}
        for pid, pc in self.pieces.items():
            if pc.get("exterieur"):
                continue
            z = self.z0 + self.niveau(pid) * self.H
            r = self.R.rect(pc["rect"])
            if pid != "palier":
                sols.append({"piece": pid, "rect": [r2(v) for v in r], "z": r2(z), "escalier": bool(pc.get("escalier"))})
            if pid != "palier":
                par_niveau.setdefault(z, []).append((pid, pc["rect"]))
        for z, rects in par_niveau.items():
            lignes = {}
            for pid, (x0, y0, x1, y1) in rects:
                for cle, a, b in ((("h", y0), x0, x1), (("h", y1), x0, x1), (("v", x0), y0, y1), (("v", x1), y0, y1)):
                    lignes.setdefault(cle, []).append([a, b])
            ouvertures = {}
            for p in self.L["portes"]:
                if p.get("escalier"):
                    continue
                if self.z0 + self.niveau(p["entre"][0]) * self.H != z and self.z0 + self.niveau(p["entre"][1]) * self.H != z:
                    continue
                (x0, y0), (x1, y1) = p["segment"]
                if y0 == y1:
                    ouvertures.setdefault(("h", y0), []).append(sorted([x0, x1]))
                else:
                    ouvertures.setdefault(("v", x0), []).append(sorted([y0, y1]))
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
                        p0, p1 = ((ma, c), (mb, c)) if sens == "h" else ((c, ma), (c, mb))
                        w0, w1 = self.R.p(*p0), self.R.p(*p1)
                        murs.append([[r2(w0[0]), r2(w0[1])], [r2(w1[0]), r2(w1[1])], r2(z)])
        for p in self.L["portes"]:
            if p.get("escalier"):
                continue
            a = p["entre"][0] if not self.pieces.get(p["entre"][0], {}).get("exterieur") else p["entre"][1]
            z = self.z0 + self.niveau(a) * self.H
            w0, w1 = (self.R.p(*q) for q in p["segment"])
            cadres.append([[r2(w0[0]), r2(w0[1])], [r2(w1[0]), r2(w1[1])], r2(z)])
        for f in self.L["fenetres"]:
            z = self.z0 + self.niveau(f["piece"]) * self.H
            w0, w1 = (self.R.p(*q) for q in f["segment"])
            vitres.append([[r2(w0[0]), r2(w0[1])], [r2(w1[0]), r2(w1[1])], r2(z), 1 if f.get("vitrine") else 0])
        for m in self.L["mobilier"]:
            z0 = m.get("z", 0)
            if z0 >= coupe:
                continue
            b = m["boite"]
            r = self.R.rect(b[:4])
            meubles.append({"nom": m["nom"], "rect": [r2(v) for v in r], "z": r2(self.z0 + self.niveau(m["piece"]) * self.H + z0), "h": r2(min(b[4], coupe - z0))})
        for pid, pc in self.pieces.items():
            if pid == "palier" or pc.get("exterieur") or pc.get("escalier"):
                continue
            noms.append([pid, self.pt(pid, self.centre(pid))])
        return {"sols": sols, "murs": murs, "cadres": cadres, "vitres": vitres, "meubles": meubles, "noms": noms}

    def appareils(self):
        out = {}
        for k, v in self.L["appareils"].items():
            if isinstance(v, str):
                out[k] = v
            else:
                piece = next((pid for pid, pc in self.pieces.items() if not pc.get("exterieur") and
                              pc["rect"][0] <= v[0] <= pc["rect"][2] and pc["rect"][1] <= v[1] <= pc["rect"][3]), None)
                out[k] = self.pt(piece or next(iter(self.pieces)), v[:2], v[2])
        return out

    def emplacement(self, texte, monde):
        S = self.L["supports"]
        if any(texte.startswith(k) for k in S.get("sur_soi") or S.get("porte_par_thomas", [])) or texte.startswith("poche"):
            return {"porte": True}
        if "local poubelles" in texte:
            b = monde.batiments["immeuble-austerlitz"]
            lp = Repere(b["origine"], b["rotation"]).rect(b["local_poubelles"])
            return {"p": [r2(lp[0] + 1.0), r2(lp[1] + 1.0), 0.3], "piece": "local-poubelles"}
        if " / " in texte:
            piece, reste = texte.split(" / ", 1)
            for motif, pt in S.get(piece, []):
                if motif in reste:
                    return {"p": self.pt(piece, pt[:2], pt[2]), "piece": piece}
            if piece in self.pieces:
                return {"p": self.pt(piece, self.centre(piece)), "piece": piece, "approche": True}
        for motif, piece, pt in S.get("sans_piece", []):
            if motif in texte:
                return {"p": self.pt(piece, pt[:2], pt[2]), "piece": piece}
        return None

    def distances_plan(self):
        out = []
        for l in self.fiche["domicile"]["plan"]["liaisons"]:
            a, b = l["a"], l["b"]
            porte = self.portes.get((a, b))
            if not porte:
                out.append((a, b, l["distance_m"], None))
                continue
            if porte.get("escalier"):
                out.append((a, b, l["distance_m"], r2(longueur(self.escalier_pts(a, b)))))
                continue
            ca, cb = self.centre(a), self.centre(b)
            out.append((a, b, l["distance_m"], round(math.dist(ca, porte["milieu"]) + math.dist(porte["milieu"], cb), 1)))
        return out


class Monde:
    def __init__(self, geo):
        self.geo = geo
        self.terrain = Terrain(geo["terrain"])
        self.batiments = {b["id"]: b for b in geo["batiments"]}
        self.logements = {}      # identifiant du logement → Logement
        self.par_personnage = {}  # personnage → ses logements (un, ou plusieurs lieux : boutique et maison)
        self.fiches = {}
        for L in geo["logements"]:
            if L["personnage"] not in self.fiches:
                self.fiches[L["personnage"]] = json.load(open(os.path.join(RACINE, "data", "personnages", f"{L['personnage']}.json"), encoding="utf-8"))
            bat = self.batiments[L["batiment"]]
            z0 = r2(self.terrain.z(*bat["origine"]))
            LG = Logement(L, bat, self.fiches[L["personnage"]], z0)
            self.logements[L["id"]] = LG
            self.par_personnage.setdefault(L["personnage"], []).append(LG)
        Q = geo["quartier"]
        self.descente = self.terrain.p3(Q["parcours_course"]["descente"])
        self.quai = [[x, y, geo["terrain"]["z_bas"]] for x, y in Q["quai"]]
        self.trajet_epicerie = self.terrain.p3(Q["trajet_epicerie"]["points"])

    # ---------------------------------------------------------------- escalier de l'immeuble de Thomas
    def escalier_volees(self, bat, sens, niveau_haut):
        E, H = bat["escalier"], bat["hauteur_etage"]
        xa, xd = sum(E["volee_montante"]["x"]) / 2, sum(E["volee_descendante"]["x"]) / 2
        y0, y1 = E["volee_montante"]["y"]
        ym = (E["palier_intermediaire"][1] + E["palier_intermediaire"][3]) / 2
        pts = []
        for k in range(niveau_haut, 0, -1):
            z = k * H
            pts += [[xd, y0, z], [xd, y1, z - H / 2], [(xa + xd) / 2, ym, z - H / 2], [xa, y1, z - H / 2], [xa, y0, z - H]]
        porte = bat["porte"]
        xp = (porte[0][0] + porte[1][0]) / 2
        pts += [[xp, 5.0, 0.0], [xp, 0.0, 0.0], [xp, -0.9, 0.0]]
        pts = [[r2(v) for v in p] for p in pts]
        return pts if sens == "descente" else pts[::-1]

    def detour_poubelles(self, bat):
        lp = bat["local_poubelles"]
        xa = sum(bat["escalier"]["volee_montante"]["x"]) / 2
        return [[xa + 1.2, 6.8, 0.0], [lp[0] + 1.0, 6.8, 0.0], [lp[0] + 1.0, lp[1] + 0.6, 0.0], [lp[0] + 1.0, 6.8, 0.0]]

    # ---------------------------------------------------------------- bâti généré
    def bati_genere(self):
        G = self.geo
        exclus = []
        for b in G["batiments"]:
            r = Repere(b["origine"], b["rotation"]).rect(b["emprise"])
            exclus.append([r[0] - 1, r[1] - 1, r[2] + 1, r[3] + 1])
            if "cour" in b:
                exclus.append(Repere(b["origine"], b["rotation"]).rect(b["cour"]))
        for r in G.get("reperes_batis", []):
            exclus.append([r["rect"][0] - 1, r["rect"][1] - 1, r["rect"][2] + 1, r["rect"][3] + 1])
        places = [p["contour"] for p in G.get("places", [])]

        def dans_poly(x, y, poly):
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            return min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys)

        def dist_seg(p, a, b):
            ax, ay = a
            bx, by = b
            dx, dy = bx - ax, by - ay
            l2 = dx * dx + dy * dy
            t = 0 if l2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / l2))
            return math.dist(p, (ax + t * dx, ay + t * dy))

        def libre(coins, rue_id):
            for x, y in coins + [[sum(c[0] for c in coins) / 4, sum(c[1] for c in coins) / 4]]:
                for e in exclus:
                    if e[0] <= x <= e[2] and e[1] <= y <= e[3]:
                        return False
                for poly in places:
                    if dans_poly(x, y, poly):
                        return False
                for r in G["rues"]:
                    if r["id"] == rue_id:
                        continue
                    for a, b in zip(r["axe"], r["axe"][1:]):
                        if dist_seg((x, y), a, b) < r["facade_a_facade"] / 2 + 0.5:
                            return False
            return True

        out = []
        sources = [(r["id"], r["axe"], r["facade_a_facade"] / 2, (1, -1), r.get("hauteurs", [14, 23]), r.get("profondeurs", [10, 15])) for r in G["rues"] if r.get("bati")]
        Q = G["quartier"]
        sources.append(("quai-est", Q["quai"], 22, (-1,), [14, 23], [10, 15]))
        sources.append(("rive-droite", [[x + Q["saone"]["rive_lointaine"], y] for x, y in Q["quai"]], 12, (1,), [14, 23], [10, 15]))
        for rid, axe, demi, cotes, hauteurs, profondeurs in sources:
            for a, b in zip(axe, axe[1:]):
                l = math.dist(a, b)
                ux, uy = (b[0] - a[0]) / l, (b[1] - a[1]) / l
                nx, ny = -uy, ux
                for cote in cotes:
                    s = 0.0
                    while s < l - 4:
                        w = 7 + 9 * h01(rid, s, cote)
                        w = min(w, l - s)
                        d = profondeurs[0] + (profondeurs[1] - profondeurs[0]) * h01(rid, s, cote, "p")
                        hgt = hauteurs[0] + (hauteurs[1] - hauteurs[0]) * h01(rid, s, cote, "h")
                        o0, o1 = demi, demi + d
                        coins = [[a[0] + ux * s + nx * cote * o0, a[1] + uy * s + ny * cote * o0],
                                 [a[0] + ux * (s + w) + nx * cote * o0, a[1] + uy * (s + w) + ny * cote * o0],
                                 [a[0] + ux * (s + w) + nx * cote * o1, a[1] + uy * (s + w) + ny * cote * o1],
                                 [a[0] + ux * s + nx * cote * o1, a[1] + uy * s + ny * cote * o1]]
                        if libre(coins, rid):
                            z0 = self.terrain.z((coins[0][0] + coins[1][0]) / 2, (coins[0][1] + coins[1][1]) / 2)
                            out.append([[[r2(x), r2(y)] for x, y in coins], r2(z0), r2(hgt)])
                        s += w + 0.0
        return out

    def arbres(self):
        G, out = self.geo, []
        for r in G["rues"]:
            pas = r.get("arbres_tous_les_m")
            if not pas:
                continue
            pts = r["axe"]
            L = longueur(pts)
            s = pas / 2
            while s < L:
                x, y = point_a(pts, s)
                out.append([r2(x), r2(y), r2(self.terrain.z(x, y))])
                s += pas
        for p in G.get("places", []):
            for x, y in p.get("arbres", []):
                out.append([x, y, r2(self.terrain.z(x, y))])
        Q = G["quartier"]
        pas = Q["arbres_quai_tous_les_m"]
        L = longueur(Q["quai"])
        s = 10
        while s < L:
            x, y = point_a(Q["quai"], s)
            out.append([r2(x + 12), r2(y), G["terrain"]["z_bas"]])
            s += pas
        return out

    def saone(self):
        Q, z = self.geo["quartier"], self.geo["terrain"]["z_bas"] - 1
        proche = [[x + Q["saone"]["rive_proche"], y, z] for x, y in Q["quai"]]
        loin = [[x + Q["saone"]["rive_lointaine"], y, z] for x, y in Q["quai"]]
        return {"proche": proche, "loin": loin}

    def rhone(self):
        Rh = self.geo["quartier"].get("rhone")
        if not Rh:
            return None
        z = self.geo["terrain"]["z_bas"] - 1
        droite = [[x, y, z] for x, y in Rh["rive_droite"]]
        gauche = [[x + Rh["largeur"], y, z] for x, y in Rh["rive_droite"]]
        return {"droite": droite, "gauche": gauche}

    def rues_3d(self):
        """Axes des rues suivant le relief (un point tous les 40 m environ)."""
        out = []
        for r in self.geo["rues"]:
            pts = []
            for a, b in zip(r["axe"], r["axe"][1:]):
                n = max(1, int(math.dist(a, b) // 40))
                for k in range(n):
                    x, y = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
                    pts.append([r2(x), r2(y), r2(self.terrain.z(x, y))])
            x, y = r["axe"][-1]
            pts.append([r2(x), r2(y), r2(self.terrain.z(x, y))])
            out.append(dict(r, axe3=pts))
        return out

    def batiments_dessin(self):
        out = []
        for b in self.geo["batiments"]:
            R = Repere(b["origine"], b["rotation"])
            z0 = r2(self.terrain.z(*b["origine"]))
            d = {"id": b["id"], "emprise": [r2(v) for v in R.rect(b["emprise"])], "niveaux": b["niveaux"], "H": b["hauteur_etage"], "z0": z0}
            w0, w1 = (R.p(*q) for q in b["porte"])
            d["porte"] = [[r2(w0[0]), r2(w0[1])], [r2(w1[0]), r2(w1[1])]]
            E = b["escalier"]
            if E["type"] == "volees":
                d["cage"] = R.rect(b["cage_escalier"])
                d["allee"] = R.rect(b["allee"])
                d["local_poubelles"] = R.rect(b["local_poubelles"])
                d["cour"] = R.rect(b["cour"])
                d["volees"] = {"montante": E["volee_montante"], "descendante": E["volee_descendante"], "palier": E["palier_intermediaire"],
                               "palier_niveau": E["palier_niveau"], "marches": E["marches_par_volee"], "jusqua": E["jusqua_niveau"]}
            else:
                bas, haut = R.p(*E["bas"]), R.p(*E["haut"])
                d["escalier_droit"] = {"bas": [r2(bas[0]), r2(bas[1]), r2(z0 + E["depuis_niveau"] * b["hauteur_etage"])],
                                       "haut": [r2(haut[0]), r2(haut[1]), r2(z0 + E["jusqua_niveau"] * b["hauteur_etage"])],
                                       "marches": E["marches"], "largeur": E["largeur"], "dir_largeur": [r2(v) for v in R.v(1, 0)]}
            if b.get("enseigne"):
                d["enseigne"] = b["enseigne"]
            if b.get("jardin"):
                d["jardin"] = [r2(v) for v in R.rect(b["jardin"])]
            out.append(d)
        return out


# -------------------------------------------------------------------- trajets d'un personnage
def trajets_course(pas, M, exclus=()):
    """Points du parcours de course pour chaque pas passé dehors en courant (hors courses et sorties à pied déjà placées)."""
    desc, quai = M.descente, M.quai
    L_desc, L_quai = longueur(desc), longueur(quai)
    ext = [k for k, s in enumerate(pas) if s["lieu"] == "exterieur" and s["activite"] != "Courses à l'épicerie" and k not in exclus]
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
            pts = sous_chemin(quai, a0, demi) + sous_chemin(quai, demi, a1)[1:] if c0 < demi < c1 else sous_chemin(quai, a0, a1)
        out[k] = pts
    return out


def plan_hors_logement(pas, M, perso, LGS, piece_lg):
    """Trajets hors des logements d'un personnage : en voiture et à pied (trajets_personnages du monde).

    Un pas appartient à un itinéraire à pied par son activité (« activites ») ou par sa rue (« pieces »).
    Renvoie, pour chaque pas concerné, les points du trajet et la zone de la vue."""
    TR = M.geo.get("trajets_personnages", {}).get(perso)
    out = {}
    if not TR:
        return out
    T3 = lambda pts: [[r2(x), r2(y), r2(M.terrain.z(x, y))] for x, y in pts]
    lieux_voiture = {"epicerie": "cour-epicerie", "maison": "garage"}
    pieces_lieu, activites = {}, {}
    for nom, it in TR["a_pied"].items():
        for pc in it["pieces"]:
            pieces_lieu[pc] = nom
        for a in it.get("activites", []):
            activites[a] = nom

    def itineraire(s):
        if piece_lg.get(s["piece"]) is not None or s["activite"] == "Courses à l'épicerie":
            return None
        return activites.get(s["activite"]) or pieces_lieu.get(s["piece"])
    contexte_it = {"cinema": "parking-cite", "monts": "parking-poleymieux"}

    def contexte(s):
        lg = piece_lg.get(s["piece"])
        if lg is not None:
            return lieux_voiture.get(lg.L.get("lieu"))
        return contexte_it.get(pieces_lieu.get(s["piece"]))

    def dist(s, moyen):
        return sum(p["distance_m"] for p in s.get("deplacement", {}).get("parcours", []) if (p["moyen"] == "voiture") == (moyen == "voiture"))

    k = 0
    while k < len(pas):
        s = pas[k]
        if s["lieu"] == "trajet-voiture":
            j = k
            while j < len(pas) and pas[j]["lieu"] == "trajet-voiture":
                j += 1
            de = contexte(pas[k - 1]) if k > 0 else None
            a = contexte(pas[j]) if j < len(pas) else None
            route, sens = None, 1
            for nom, R in TR["voiture"].items():
                if (R["de"], R["a"]) == (de, a):
                    route, sens = nom, 1
                elif (R["de"], R["a"]) == (a, de):
                    route, sens = nom, -1
            if route is None:
                raise SystemExit(f"{perso} : trajet en voiture inconnu de {de} à {a} ({pas[k]['heure']})")
            pts = T3(TR["voiture"][route]["points"])
            if sens < 0:
                pts = pts[::-1]
            L = longueur(pts)
            total = sum(dist(pas[i], "voiture") for i in range(k, j)) or 1
            cumul = 0.0
            zone = {"boutique-maison": "trajet", "maison-cinema": "trajet", "maison-monts": "route-monts"}[route]
            for i in range(k, j):
                c0, c1 = cumul, cumul + dist(pas[i], "voiture")
                cumul = c1
                out[i] = {"w": sous_chemin(pts, c0 / total * L, c1 / total * L), "zone": zone, "cont": True, "route": route}
            k = j
            continue
        it_nom = itineraire(s)
        if it_nom:
            it = TR["a_pied"][it_nom]
            j = k
            while j < len(pas) and itineraire(pas[j]) == it_nom:
                j += 1
            pts = T3(it["points"])
            L = longueur(pts)
            total = sum(dist(pas[i], "marche") for i in range(k, j)) or 1
            cumul = 0.0
            for i in range(k, j):
                zone = it.get("zone_par_lieu", {}).get(pas[i]["lieu"]) or it.get("zone") or \
                    {"banque": "rue", "cinema": "cinema", "vote": "villeurbanne", "monts": "monts"}[it_nom]
                c0, c1 = cumul, cumul + dist(pas[i], "marche")
                cumul = c1
                if it.get("aller_retour"):
                    a0, a1 = c0 / total * 2 * L, c1 / total * 2 * L
                    pa, pb = (a0 if a0 <= L else 2 * L - a0), (a1 if a1 <= L else 2 * L - a1)
                    w = sous_chemin(pts, pa, L) + sous_chemin(pts, L, pb)[1:] if a0 < L < a1 else sous_chemin(pts, pa, pb)
                else:
                    w = sous_chemin(pts, c0 / total * L, c1 / total * L)
                out[i] = {"w": w, "zone": zone, "cont": c1 > c0}
            k = j
            continue
        k += 1
    return out


def exporter_personnage(perso, M, emplacements, noms, avertissements):
    LGS = M.par_personnage[perso]
    LG = LGS[0]
    fiche = M.fiches[perso]
    bat = LG.bat
    piece_lg = {}
    for L_ in LGS:
        for pid in L_.pieces:
            piece_lg.setdefault(pid, L_)
    plusieurs = len(LGS) > 1
    TR = M.geo.get("trajets_personnages", {}).get(perso, {})
    fichiers = sorted(glob.glob(os.path.join(RACINE, "data", "timelines", perso, "*.json")))
    jours, precedent, hors = [], None, False

    def note(t):
        if t in emplacements:
            return
        e, approx = None, None
        for L_ in LGS:
            x = L_.emplacement(t, M)
            if x and not x.get("approche"):
                e = x
                break
            if x and approx is None:
                approx = x
        if e is None and t in TR.get("emplacements", {}):
            x, y, dz = TR["emplacements"][t]
            e = {"p": [r2(x), r2(y), r2(M.terrain.z(x, y) + dz)], "piece": t.split(" / ")[0]}
        if e is None and approx is not None:
            e = approx
            avertissements.append(f"{perso} : emplacement placé au centre de la pièce « {t} »")
        if e is None:
            avertissements.append(f"{perso} : emplacement inconnu « {t} »")
            e = {"p": LG.pt(next(iter(LG.pieces)), LG.centre(next(iter(LG.pieces)))), "approche": True}
        emplacements[t] = e

    lp = M.geo.get("lieux_publics", {})
    mes_logements = {L_.L["id"] for L_ in LGS}
    for fn in fichiers:
        J = json.load(open(fn, encoding="utf-8"))
        pas = J["pas"]
        for t in J["etat_initial"]["positions"].values():
            note(t)
        dehors = plan_hors_logement(pas, M, perso, LGS, piece_lg) if TR else {}
        course = trajets_course(pas, M, exclus=set(dehors)) if not plusieurs else {}
        if precedent is None:
            L0 = piece_lg[J["etat_initial"]["piece"]]
            pt, _ = L0.poste(J["etat_initial"]["piece"], "allongé", "")
            precedent = {"pt": pt, "piece": J["etat_initial"]["piece"], "lg": L0}
        traj, s_epi, alle = M.trajet_epicerie, 0.0, False
        L_epi = longueur(traj)
        sortie = []
        for k, s in enumerate(pas):
            dep = s.get("deplacement", {})
            esc = dep.get("escalier", {}).get("sens")
            chemin = dep.get("chemin") or []
            dist = sum(p["distance_m"] for p in dep.get("parcours", []))
            courses = s["activite"] == "Courses à l'épicerie"
            poubelles = any("local poubelles" in o["vers"] for o in s.get("objets", []))
            w, cont, d, zone = None, False, None, None
            lg = piece_lg.get(s["piece"])
            public = s["lieu"] in lp and lp[s["lieu"]]["logement"] not in mes_logements
            if public:
                # dans un lieu public : le poste prévu dans le logement d'un autre habitant
                P = lp[s["lieu"]]
                autre = M.logements[P["logement"]]
                po = autre.L["postes"][P["piece"]][P["poste"]]
                cible = autre.pt(P["piece"], po[:2])
                dd = autre.R.v(po[2], po[3])
                d = [r2(dd[0]), r2(dd[1]), 0.0]
                w = [precedent["pt"], traj[-1], cible] if precedent["pt"] != cible else None
                precedent = {"pt": cible, "piece": s["piece"], "lg": None}
                alle, hors, s_epi = True, True, L_epi
                zone = "lg:" + autre.L["id"]
            elif lg is not None and (s["lieu"] in ("domicile", "exterieur") or s["lieu"] in lp or plusieurs or s["piece"] in LG.pieces):
                po_pt, d = lg.poste(s["piece"], s["posture"], s["activite"])
                zone = "lg:" + lg.L["id"]
                if esc == "montee" and lg.bat["escalier"]["type"] == "volees" and not dep.get("escalier", {}).get("interieur"):
                    rue = []
                    if courses and dist:
                        rue = sous_chemin(traj, min(L_epi, s_epi), max(0.0, s_epi - dist))
                        s_epi = 0.0
                        cont = True
                    pieces = chemin if chemin else ["palier", s["piece"]]
                    w = rue + M.escalier_volees(lg.bat, "montee", lg.base) + lg.traversee(pieces) + [po_pt]
                else:
                    depart = precedent["piece"]
                    pieces = chemin if chemin else lg.chemin_pieces(depart, s["piece"])
                    if pieces and pieces[0] != depart and not hors and depart in lg.pieces and precedent.get("lg") is lg:
                        pieces = lg.chemin_pieces(depart, pieces[0]) + pieces[1:]
                    entree = []
                    if hors and pieces and pieces[0] in lg.L.get("sorties", {}):
                        entree = [lg.pt(pieces[0], lg.L["sorties"][pieces[0]])]
                    w = [precedent["pt"]] + entree + lg.traversee(pieces) + [po_pt]
                hors = False
                precedent = {"pt": po_pt, "piece": s["piece"], "lg": lg}
            elif k in dehors:
                x = dehors[k]
                zone = x["zone"]
                pre = []
                lgp = precedent.get("lg") if not hors else None
                if lgp is not None and esc == "descente" and lgp.bat.get("escalier", {}).get("type") == "volees":
                    # sortie de l'immeuble par la cage d'escalier
                    pieces = chemin if chemin else [precedent["piece"], "palier"]
                    pre = lgp.traversee(pieces) + M.escalier_volees(lgp.bat, "descente", lgp.base)
                elif lgp is not None and chemin:
                    pieces = [p_ for p_ in chemin if p_ in lgp.pieces]
                    pre = lgp.traversee(pieces)
                    if pieces and pieces[-1] in lgp.L.get("sorties", {}):
                        pre.append(lgp.pt(pieces[-1], lgp.L["sorties"][pieces[-1]]))
                w = [precedent["pt"]] + pre + x["w"]
                cont = x["cont"]
                if len(x["w"]) > 1:
                    a_, b_ = x["w"][-2], x["w"][-1]
                    d = [r2(b_[0] - a_[0]), r2(b_[1] - a_[1]), 0.0]
                precedent = {"pt": w[-1], "piece": s["piece"], "lg": None}
                hors = True
            else:
                if esc == "descente":
                    pieces = chemin if chemin else [precedent["piece"], "palier"]
                    if pieces[0] != precedent["piece"] and precedent["piece"] in LG.pieces:
                        pieces = LG.chemin_pieces(precedent["piece"], pieces[0]) + pieces[1:]
                    descente = M.escalier_volees(bat, "descente", LG.base)
                    if poubelles:
                        descente = descente[:-3] + M.detour_poubelles(bat) + descente[-3:]
                    w = [precedent["pt"]] + LG.traversee(pieces) + descente
                    precedent = {"pt": descente[-1], "piece": "rue", "lg": None}
                if courses:
                    fin_seg = max(0.0, s_epi - dist) if alle else min(L_epi, s_epi + dist)
                    seg = sous_chemin(traj, s_epi, fin_seg)
                    s_epi = fin_seg
                    w = (w or [precedent["pt"]]) + seg
                    cont = True
                    zone = "rue"
                elif k in course:
                    w = (w or []) + course[k]
                    cont = True
                    zone = "parcours"
                elif plusieurs:
                    avertissements.append(f"{perso} : pas hors des logements sans trajet connu ({J['meta']['date']} {s['heure']}, {s['piece']})")
                if w:
                    precedent = {"pt": w[-1], "piece": "rue", "lg": None}
                hors = True
            if not courses:
                alle, s_epi = False, 0.0
            if w:
                propre = [w[0]]
                for p in w[1:]:
                    if math.dist(p, propre[-1]) > 0.01:
                        propre.append(p)
                w = propre
            for o in s.get("objets", []):
                note(o["de"])
                note(o["vers"])
            nouveaux = []
            for o in s.get("nouveaux_objets", []):
                noms[o["id"]] = o["nom"]
                note(o["position"])
                nouveaux.append([o["id"], o["position"]])
            code = "v" if s["lieu"] == "trajet-voiture" else ("p" if public else ("d" if lg is not None else "e"))
            e = {"h": s["heure"], "pc": s["piece"], "l": code,
                 "po": POSES.get(s["posture"], "debout"), "a": s["activite"], "x": s["action"],
                 "b": [round(s["besoins"][n], 1) for n in BESOINS], "em": [round(s["emotions"][n], 3) for n in EMOTIONS],
                 "ap": s.get("appareils_allumes", [])}
            if zone:
                e["zn"] = zone
            for cle, src in (("pe", "pensee"), ("r", "reve"), ("ps", "phase_sommeil")):
                if s.get(src):
                    e[cle] = s[src]
            if s.get("evenements"):
                e["ev"] = [v["id"] for v in s["evenements"]]
            if s.get("objets"):
                e["ob"] = [[o["objet"], o["de"], o["vers"]] for o in s["objets"]]
            if nouveaux:
                e["no"] = nouveaux
            if s.get("achats"):
                e["ac"] = [[a["nom"], a["quantite"], a["unite"], a.get("prix", 0)] for a in s["achats"]]
            if s.get("ventes"):
                e["ve"] = [round(sum(v["prix"] for v in s["ventes"]), 2), s.get("clients", 0)]
            if s.get("argent"):
                e["ar"] = s["argent"]["soldes"]
            if w and len(w) > 1:
                e["w"] = w
            if cont:
                e["cont"] = 1
            if esc:
                e["esc"] = esc
            if d:
                e["d"] = [r2(v) for v in d]
            if hors:
                e["hors"] = 1
            sortie.append(e)
        eph = fiche["meta"]["ephemerides_lyon_approximatives"].get(J["meta"]["date"], {})
        jours.append({"date": J["meta"]["date"], "jour": J["meta"]["jour"],
                      "methode": "agent" if any("agent" in m for m in J["meta"].get("methode", [])) else "reference",
                      "lever": eph.get("lever_soleil"), "coucher": eph.get("coucher_soleil"),
                      "positions": J["etat_initial"]["positions"], "pas": sortie})
    J0 = json.load(open(fichiers[0], encoding="utf-8"))
    L0 = piece_lg[J0["etat_initial"]["piece"]]
    p0, _ = L0.poste(J0["etat_initial"]["piece"], "allongé", "")
    appareils = {}
    for L_ in LGS:
        appareils.update(L_.appareils())
    return {"id": perso, "nom": f"{fiche['identite']['prenom']} {fiche['identite']['nom']}", "prenom": fiche["identite"]["prenom"],
            "logement": L0.L["id"], "logements": [L_.L["id"] for L_ in LGS], "batiment": L0.bat["id"],
            "batiments": {L_.L["id"]: L_.bat["id"] for L_ in LGS}, "depart": p0,
            "noms_pieces": {p["id"]: p["nom"] for p in fiche["domicile"]["pieces"]},
            "evenements": {k: v["description"] for k, v in fiche["modele_emotionnel"]["evenements"].items()},
            "besoins": [{"id": n, "seuil": fiche["besoins"][n]["seuil_alerte"]} for n in BESOINS],
            "appareils": appareils, "jours": jours}


def exporter(chemin_monde, sortie):
    geo = json.load(open(chemin_monde, encoding="utf-8"))
    M = Monde(geo)
    erreurs, avertissements = [], []
    for perso, LGS in M.par_personnage.items():
        fiche = M.fiches[perso]
        for p in fiche["domicile"]["pieces"]:
            LG = next((L_ for L_ in LGS if p["id"] in L_.pieces), None)
            if LG is None:
                erreurs.append(f"{perso} : pièce sans rectangle {p['id']}")
            else:
                x0, y0, x1, y1 = LG.pieces[p["id"]]["rect"]
                if abs((x1 - x0) * (y1 - y0) - p["surface_m2"]) > 0.05:
                    avertissements.append(f"{perso} : {p['id']} fait {round((x1 - x0) * (y1 - y0), 2)} m² sur le plan, {p['surface_m2']} m² dans la fiche")
        for l in fiche["domicile"]["plan"]["liaisons"]:
            if not any((l["a"], l["b"]) in L_.portes for L_ in LGS):
                erreurs.append(f"{perso} : liaison sans porte {l['a']} – {l['b']}")
    if erreurs:
        for e in erreurs:
            print("ERREUR : " + e)
        sys.exit(1)

    personnages, emplacements, objets = [], {}, {}
    for perso in M.par_personnage:
        emplacements[perso], objets[perso] = {}, {o["id"]: o["nom"] for o in M.fiches[perso]["objets"]}
        if not glob.glob(os.path.join(RACINE, "data", "timelines", perso, "*.json")):
            avertissements.append(f"{perso} : aucune journée générée")
            continue
        personnages.append(exporter_personnage(perso, M, emplacements[perso], objets[perso], avertissements))

    donnees = {
        "monde": {
            "statut": geo["meta"]["statut"], "terrain": geo["terrain"], "rues": M.rues_3d(), "places": geo.get("places", []),
            "batiments": M.batiments_dessin(), "logements": {LG.L["id"]: LG.dessin() for LG in M.logements.values()},
            "bati": M.bati_genere(), "arbres": M.arbres(), "saone": M.saone(), "rhone": M.rhone(), "quai": M.quai, "descente": M.descente,
            "trajet_epicerie": M.trajet_epicerie, "reperes": geo["quartier"]["reperes"],
            "reperes_batis": [dict(r, z0=r2(M.terrain.z((r["rect"][0] + r["rect"][2]) / 2, (r["rect"][1] + r["rect"][3]) / 2))) for r in geo.get("reperes_batis", [])],
            "trajets": {perso: {"voiture": {k: [[r2(x), r2(y), r2(M.terrain.z(x, y))] for x, y in R["points"]] for k, R in T["voiture"].items()},
                                "a_pied": {k: [[r2(x), r2(y), r2(M.terrain.z(x, y))] for x, y in R["points"]] for k, R in T["a_pied"].items()},
                                "lieux": T["lieux"]}
                        for perso, T in geo.get("trajets_personnages", {}).items()},
        },
        "personnages": personnages, "emplacements": emplacements, "objets": objets, "emotions": EMOTIONS,
    }
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    with open(sortie, "w", encoding="utf-8") as f:
        f.write("window.PARADOXE = ")
        json.dump(donnees, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"{len(personnages)} personnages, {sum(len(j['pas']) for p in personnages for j in p['jours'])} pas, "
          f"{len(donnees['monde']['bati'])} immeubles générés, {len(donnees['monde']['arbres'])} arbres → {os.path.relpath(sortie, RACINE)}")
    for perso, LGS in M.par_personnage.items():
        print(f"Distances entre pièces, {perso} (fiche / plan) :")
        for LG in LGS:
            for a, b, f_, p_ in LG.distances_plan():
                if a in LG.pieces and b in LG.pieces:
                    print(f"  {a:>16} – {b:<16} {f_:>4} m / {p_} m")
    for a in avertissements:
        print("  ! " + a)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--monde", default=os.path.join(RACINE, "data", "monde", "croix-rousse.json"))
    ap.add_argument("--sortie", default=os.path.join(RACINE, "vue", "donnees.js"))
    a = ap.parse_args()
    exporter(a.monde, a.sortie)
