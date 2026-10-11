"""Compare une journée simulée à une journée de référence, pas à pas.

Usage : python3 outils/comparer_journees.py REFERENCE.json SIMULATION.json [--details]

Faits comparés à chaque pas : pièce, lieu, posture, appareils et lumières
allumés, position de chaque objet, stock de chaque provision. Les besoins et
les émotions sont comparés en écart moyen. Les textes (actions, pensées) ne
sont pas comparés.
"""
import json
import sys


def positions_par_pas(j):
    pos = dict(j["etat_initial"]["positions"])
    stock = dict(j["etat_initial"]["stock"])
    out = []
    for s in j["pas"]:
        for o in s.get("nouveaux_objets", []):
            pos[o["id"]] = o["position"]
        for o in s.get("objets", []):
            pos[o["objet"]] = o["vers"]
        for cle in ("production", "consommation"):
            for x in s.get(cle, []):
                if "reste" in x:
                    stock[x["produit"]] = x["reste"]
        out.append((dict(pos), dict(stock)))
    return out


def plages(heures):
    """Regroupe une liste d'heures consécutives en plages."""
    if not heures:
        return ""
    res, debut, prec = [], heures[0], heures[0]
    def suivant(h):
        m = int(h[:2]) * 60 + int(h[3:]) + 5
        return f"{m // 60:02d}:{m % 60:02d}"
    for h in heures[1:]:
        if h != suivant(prec):
            res.append(debut if debut == prec else f"{debut}-{prec}")
            debut = h
        prec = h
    res.append(debut if debut == prec else f"{debut}-{prec}")
    return ", ".join(res)


def comparer(ref, sim):
    R, S = ref["pas"], sim["pas"]
    pr, ps = positions_par_pas(ref), positions_par_pas(sim)
    criteres = {"pièce": [], "lieu": [], "posture": [], "appareils": [], "objets": [], "stock": []}
    objets_diff = {}
    for k, (a, b) in enumerate(zip(R, S)):
        h = a["heure"]
        if a["piece"] != b["piece"]:
            criteres["pièce"].append(h)
        if a["lieu"] != b["lieu"]:
            criteres["lieu"].append(h)
        if a["posture"] != b["posture"]:
            criteres["posture"].append(h)
        if sorted(a["appareils_allumes"]) != sorted(b["appareils_allumes"]):
            criteres["appareils"].append(h)
        if pr[k][0] != ps[k][0]:
            criteres["objets"].append(h)
            for o in set(pr[k][0]) | set(ps[k][0]):
                if pr[k][0].get(o) != ps[k][0].get(o):
                    objets_diff.setdefault(o, []).append(h)
        if pr[k][1] != ps[k][1]:
            criteres["stock"].append(h)
    n = len(R)
    def mae(cle):
        noms = R[0][cle].keys()
        return {x: round(sum(abs(a[cle][x] - b[cle][x]) for a, b in zip(R, S)) / n, 3) for x in noms if x in S[0][cle]}
    return {
        "pas": n,
        "concordance": {c: round(100 * (n - len(v)) / n, 1) for c, v in criteres.items()},
        "differences": {c: plages(v) for c, v in criteres.items() if v},
        "objets_en_ecart": {o: plages(v) for o, v in objets_diff.items()},
        "ecart_moyen_besoins": mae("besoins"),
        "ecart_moyen_emotions": mae("emotions"),
        "etat_final_identique": {
            "positions": ref["etat_final"]["positions"] == sim["etat_final"]["positions"],
            "stock": ref["etat_final"]["stock"] == sim["etat_final"]["stock"],
            "pièce": ref["etat_final"]["piece"] == sim["etat_final"]["piece"],
        },
    }


if __name__ == "__main__":
    r = comparer(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])))
    print(json.dumps(r, ensure_ascii=False, indent=1))
