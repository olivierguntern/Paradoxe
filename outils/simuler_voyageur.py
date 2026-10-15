"""Rejoue le quartier avec le voyageur (le monde joué) et mesure la divergence avec le monde de référence.

Usage :
  python3 outils/simuler_voyageur.py data/voyageur/courses-manquees.json [--reference data/quartier]

Le monde joué est écrit dans data/voyageur/<nom>/ (une journée par habitant
et par jour, comme le quartier), avec DIVERGENCE.md et divergence.json : le
verdict, ce que le voyageur a fait, la propagation habitant par habitant,
la chaîne des causes (de l'intervention au dernier fait),
les faits heure par heure et les détails tolérés ; si le scénario porte une
mission (data/missions/<id>.json), son résultat : objectif atteint ou non,
avec ou sans paradoxe. Les habitants et la
période sont ceux du monde de référence.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from divergence import comparer_mondes, ecrire_md
from simuler_quartier import simuler
from voyageur import Voyageur

sys.stdout.reconfigure(encoding="utf-8")
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def evaluer_mission(mid, v, verdict):
    """La mission (data/missions/<id>.json) : objectif atteint dans le monde joué (avancement du voyageur), sans verdict
    interdit. Parfaite si aucun fait de la vie des habitants n'a changé."""
    M = json.load(open(os.path.join(RACINE, "data", "missions", f"{mid}.json"), encoding="utf-8"))
    manque = {k: val for k, val in M["objectif"].items() if v.avancement.get(k) != val}
    interdit = next((x for x in M.get("contraintes", {}).get("verdicts_interdits", []) if verdict.startswith(x)), None)
    if manque:
        resultat, raison = "échouée", "Objectif non atteint : " + ", ".join(f"{k} doit être « {val} » (est « {v.avancement.get(k, 'rien')} »)" for k, val in manque.items()) + "."
    elif interdit:
        resultat, raison = "échouée", f"L'objectif est atteint, mais au prix d'un {interdit} : {verdict}."
    elif verdict.startswith("aucune divergence"):
        resultat, raison = "réussie, parfaitement", M.get("reussite_parfaite", "Objectif atteint sans aucun fait changé.")
    else:
        resultat, raison = "réussie", f"Objectif atteint ; la divergence reste sous le seuil du paradoxe : {verdict}."
    return {"id": mid, "titre": M["titre"], "resultat": resultat, "reussie": resultat.startswith("réussie"), "raison": raison,
            "avancement": v.avancement, "echecs": v.echecs, "avenir": avenir(M, v.avancement, verdict)}


def avenir(M, avancement, verdict):
    """L'avenir après la semaine (avenirs de la mission) : le premier qui convient à l'avancement et au verdict, ou None."""
    for a in M.get("avenirs", []):
        if any(avancement.get(k, "rien") != val for k, val in a.get("si", {}).items()):
            continue
        if any(verdict.startswith(x) for x in a.get("sauf_verdicts", [])):
            continue
        if a.get("verdicts") and not any(verdict.startswith(x) for x in a["verdicts"]):
            continue
        n = a.get("nuances", {})
        nuance = next((t for k, t in n.items() if k != "autrement" and verdict.startswith(k)), n.get("autrement"))
        return {"id": a["id"], "titre": a["titre"], "frise": a["frise"], "nuance": nuance}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--reference", default="data/quartier")
    a = ap.parse_args()
    scenario = json.load(open(a.scenario, encoding="utf-8"))
    dossier = os.path.splitext(a.scenario)[0]
    personnages = sorted(d for d in os.listdir(a.reference) if os.path.isdir(os.path.join(a.reference, d)))
    dates = sorted(f[:-5] for f in os.listdir(os.path.join(a.reference, personnages[0])) if f.endswith(".json"))
    v = Voyageur(scenario)
    simuler(personnages, dates[0], dates[-1], dossier, v, bavard=False)
    for x in scenario["interventions"]:
        if x["type"] == "geste":
            x["_duree"] = v.duree(x)
    r = comparer_mondes(a.reference, dossier, v.cibles(), scenario["interventions"])
    if scenario.get("mission"):
        r["mission"] = evaluer_mission(scenario["mission"], v, r["verdict"])
    r["voyageur"] = [{"date": d, "heure": h, "action": t} for d, h, t in v.journal]
    json.dump(r, open(os.path.join(dossier, "divergence.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ecrire_md(r, scenario, v.journal, os.path.join(dossier, "DIVERGENCE.md"))
    print(f"{os.path.basename(dossier)} : {r['verdict']}")
    if r.get("mission"):
        print(f"  mission « {r['mission']['titre']} » : {r['mission']['resultat']} — {r['mission']['raison']}")
    for d, h, t in v.journal:
        print(f"  voyageur {d} {h} : {t}")
    for p, x in sorted(r["premier_fait"].items(), key=lambda kv: (kv[1]["date"], kv[1]["heure"])):
        print(f"  {p}{' (cascade)' if p in r['cascade'] else ''} : {x['date']} {x['heure']} {x['genre']} ({x['detail'][:90]})")


if __name__ == "__main__":
    main()
