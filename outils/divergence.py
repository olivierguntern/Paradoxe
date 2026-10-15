"""Divergence entre le monde de référence et le monde joué (avec le voyageur).

Usage : python3 outils/divergence.py data/quartier data/voyageur/<nom> [--cibles thomas-berthier ...]

Les deux mondes sont comparés pas à pas, habitant par habitant, en deux
niveaux (CONCEPTION.md, « Mesure envisagée ») :
- les faits, comptés dans la divergence : l'endroit où il est, l'activité, les
  personnes avec qui il est, la place de chaque objet, ce qu'il achète, ce
  qu'il a appris ;
- les détails, tolérés : besoins, émotions, quantités en stock (maison et
  magasin), argent. Ils sont mesurés, pas comptés.

La divergence suit, heure par heure, le nombre de faits différents (chacun
compté une fois dans l'heure, même s'il dure) et le nombre d'habitants
touchés. Un habitant touché sans être visé par une
intervention l'est par cascade. Le verdict, selon les seuils de
data/monde/paradoxe.json : aucune divergence, divergence absorbée (plus aucun
fait différent à la fin), persistante, en cascade, ou paradoxe.
"""
import datetime
import json
import os
import sys

from comparer_journees import positions_par_pas
from fiches import MONDE, lire

sys.stdout.reconfigure(encoding="utf-8")


def appris_au_pas(j, heure):
    """Ce que l'habitant a appris jusqu'à ce pas (mémoire gardée d'un jour à l'autre) : qui le lui a dit, et quoi ;
    la même chose apprise à un autre moment n'est pas une différence."""
    date = j["meta"]["date"]
    return {(x["de"], x.get("quoi")) for x in (j["etat_final"].get("habitant") or {}).get("appris", [])
            if (x["date"], x["heure"]) <= (date, heure)}


JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def quand(date, heure=None):
    """« le jeudi 11 mars, entre 18:00 et 19:00 »."""
    d = datetime.date.fromisoformat(date)
    txt = f"le {JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}"
    if heure:
        h = int(heure[:2])
        txt += f", entre {heure} et {(h + 1) % 24:02d}:00"
    return txt


def faits_du_pas(a, b, pa, pb, ja, jb):
    """Faits différents entre deux pas d'un même habitant : liste de (genre, détail)."""
    out = []
    if (a["lieu"], a["piece"]) != (b["lieu"], b["piece"]):
        out.append(("lieu", f"{a['piece']} → {b['piece']}"))
    if a["activite"] != b["activite"]:
        out.append(("activité", f"{a['activite']} → {b['activite']}"))
    ea, eb = set(a.get("ensemble", [])), set(b.get("ensemble", []))
    if ea != eb:
        out.append(("rencontre", "; ".join(([f"sans {', '.join(sorted(ea - eb))}"] if ea - eb else []) + ([f"avec {', '.join(sorted(eb - ea))}"] if eb - ea else []))))
    for o in sorted(set(pa[0]) | set(pb[0])):
        if pa[0].get(o) != pb[0].get(o):
            out.append(("objet", f"{o} : {pa[0].get(o)} → {pb[0].get(o)}"))
    aa = sorted((x["produit"], x["quantite"]) for x in a.get("achats", []))
    ab = sorted((x["produit"], x["quantite"]) for x in b.get("achats", []))
    if aa != ab:
        out.append(("achat", f"{aa} → {ab}"))
    sa, sb = appris_au_pas(ja, a["heure"]), appris_au_pas(jb, b["heure"])
    for x in sorted(sa ^ sb):
        out.append(("appris", f"{'ne sait pas' if x in sa else 'apprend'} : {x[1]}"))
    return out


def details_du_pas(a, b, pa, pb):
    """Écarts tolérés : besoins et émotions (écart absolu moyen), produits en stock et comptes différents."""
    besoins = sum(abs(a["besoins"][k] - b["besoins"][k]) for k in a["besoins"]) / len(a["besoins"])
    emotions = sum(abs(a["emotions"][k] - b["emotions"][k]) for k in a["emotions"]) / len(a["emotions"])
    stock = sum(pa[1].get(k) != pb[1].get(k) for k in set(pa[1]) | set(pb[1]))
    magasin = sum(pa[2].get(k) != pb[2].get(k) for k in set(pa[2]) | set(pb[2]))
    argent = sum(pa[3].get(k) != pb[3].get(k) for k in set(pa[3]) | set(pb[3]))
    return besoins, emotions, stock, magasin, argent


def comparer_mondes(ref, joue, cibles=()):
    S = lire(os.path.join(MONDE, "paradoxe.json"))
    habitants = sorted(d for d in os.listdir(joue) if os.path.isdir(os.path.join(joue, d)))
    dates = sorted(f[:-5] for f in os.listdir(os.path.join(joue, habitants[0])) if f.endswith(".json"))
    heures = []          # (date, heure, faits, habitants touchés)
    premier = {}         # habitant -> premier fait divergent
    par_habitant = {p: {"pas_divergents": 0, "faits": 0} for p in habitants}
    details_fin = {}
    exemples = {}
    distincts = {}       # habitant -> faits différents (genre, détail), chacun compté une fois
    for date in dates:
        J = {p: (json.load(open(os.path.join(ref, p, f"{date}.json"), encoding="utf-8")),
                 json.load(open(os.path.join(joue, p, f"{date}.json"), encoding="utf-8"))) for p in habitants}
        P = {p: (positions_par_pas(ja), positions_par_pas(jb)) for p, (ja, jb) in J.items()}
        faits_h, touches_h = set(), set()
        for k in range(len(J[habitants[0]][0]["pas"])):
            faits, touches = 0, set()
            for p in habitants:
                ja, jb = J[p]
                a, b = ja["pas"][k], jb["pas"][k]
                f = faits_du_pas(a, b, P[p][0][k], P[p][1][k], ja, jb)
                if f:
                    faits += len(f)
                    touches.add(p)
                    faits_h |= {(p, g, d) for g, d in f}
                    distincts.setdefault(p, set()).update(f)
                    par_habitant[p]["pas_divergents"] += 1
                    par_habitant[p]["faits"] = len(distincts[p])
                    premier.setdefault(p, {"date": date, "heure": a["heure"], "genre": f[0][0], "detail": f[0][1]})
                    for g, d in f:
                        exemples.setdefault(p, {}).setdefault(g, (date, a["heure"], d))
                if k == len(ja["pas"]) - 1 and date == dates[-1]:
                    details_fin[p] = details_du_pas(a, b, P[p][0][k], P[p][1][k])
            touches_h |= touches
            if k % 12 == 11:
                heures.append({"date": date, "heure": J[habitants[0]][0]["pas"][k - 11]["heure"], "faits": len(faits_h), "habitants": sorted(touches_h)})
                faits_h, touches_h = set(), set()
            dernier = (faits, sorted(touches))
    touches_total = sorted(p for p in habitants if par_habitant[p]["faits"])
    cascade = [p for p in touches_total if p not in cibles]
    max_faits = max((h["faits"] for h in heures), default=0)
    if not touches_total:
        verdict = "aucune divergence : rien n'a changé dans la vie des habitants"
    elif len(touches_total) >= S["seuil_habitants"] or max_faits >= S["seuil_faits"]:
        verdict = f"paradoxe : {len(touches_total)} habitants touchés, jusqu'à {max_faits} faits différents dans une heure"
    elif dernier[0] == 0:
        fin = next((h for h in reversed(heures) if h["faits"]), None)
        verdict = (f"absorbée : dernier fait différent {quand(fin['date'], fin['heure'])}" if fin else "absorbée")
        if cascade:
            verdict += f", après une cascade jusqu'à {', '.join(cascade)}"
    elif cascade:
        verdict = f"en cascade : la divergence a gagné {', '.join(cascade)} et dure encore à la fin"
    else:
        verdict = f"persistante : {', '.join(touches_total)} reste différent à la fin, sans cascade"
    return {"habitants": habitants, "cibles": list(cibles), "verdict": verdict, "touches": touches_total, "cascade": cascade,
            "premier_fait": premier, "par_habitant": par_habitant, "exemples": exemples, "heures": heures,
            "fin": {"faits": dernier[0], "habitants": dernier[1]},
            "details_fin": {p: {"besoins": round(v[0], 2), "emotions": round(v[1], 3), "produits_maison": v[2], "produits_magasin": v[3],
                                "comptes": v[4]} for p, v in details_fin.items()}}


def ecrire_md(r, scenario, journal, chemin):
    L = [f"# Divergence : {scenario.get('description', '')}", ""]
    if scenario.get("attendu"):
        L += [f"**Attendu.** {scenario['attendu']}", ""]
    L += [f"**Verdict : {r['verdict']}.**", "", "## Ce que le voyageur a fait", ""]
    L += [f"- {d} {h} : {t}" for d, h, t in journal] or ["- rien"]
    L += ["", "## Propagation", "", "Premier fait différent pour chaque habitant touché (habitants visés : " + (", ".join(r["cibles"]) or "aucun") + ") :", ""]
    for p, x in sorted(r["premier_fait"].items(), key=lambda kv: (kv[1]["date"], kv[1]["heure"])):
        L.append(f"- **{p}**{' (cascade)' if p in r['cascade'] else ''} : {quand(x['date'])} à {x['heure']}, {x['genre']} ({x['detail']})")
    L += ["", "## Faits par habitant", "", "| Habitant | Pas où un fait diffère | Faits différents | Premier exemple de chaque genre |", "|---|---|---|---|"]
    for p, v in r["par_habitant"].items():
        ex = " ; ".join(f"{g} {d} {h} : {t}" for g, (d, h, t) in r["exemples"].get(p, {}).items())
        L.append(f"| {p} | {v['pas_divergents']} | {v['faits']} | {ex[:400]} |")
    L += ["", "## Heure par heure", "", "Seules les heures où un fait diffère.", "", "| Date | Heure | Faits | Habitants touchés |", "|---|---|---|---|"]
    L += [f"| {h['date']} | {h['heure']} | {h['faits']} | {', '.join(h['habitants'])} |" for h in r["heures"] if h["faits"]]
    L += ["", "## Détails tolérés à la fin de la période", "", "| Habitant | Besoins (écart moyen) | Émotions (écart moyen) | Provisions différentes | Produits du magasin différents | Comptes différents |", "|---|---|---|---|---|---|"]
    for p, v in r["details_fin"].items():
        L.append(f"| {p} | {v['besoins']} | {v['emotions']} | {v['produits_maison']} | {v['produits_magasin']} | {v['comptes']} |")
    open(chemin, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    cibles = args[args.index("--cibles") + 1:] if "--cibles" in args else []
    r = comparer_mondes(args[0], args[1], cibles)
    print(r["verdict"])
    print(json.dumps({k: r[k] for k in ("touches", "cascade", "premier_fait", "par_habitant", "fin")}, ensure_ascii=False, indent=1))
