"""Rejoue le quartier avec le voyageur (le monde joué) et mesure la divergence avec le monde de référence.

Usage :
  python3 outils/simuler_voyageur.py data/voyageur/courses-manquees.json [--reference data/quartier]

Le monde joué est écrit dans data/voyageur/<nom>/ (une journée par habitant
et par jour, comme le quartier), avec DIVERGENCE.md et divergence.json : le
verdict, ce que le voyageur a fait, la propagation habitant par habitant,
les faits heure par heure et les détails tolérés. Les habitants et la
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
    r = comparer_mondes(a.reference, dossier, v.cibles())
    r["voyageur"] = [{"date": d, "heure": h, "action": t} for d, h, t in v.journal]
    json.dump(r, open(os.path.join(dossier, "divergence.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ecrire_md(r, scenario, v.journal, os.path.join(dossier, "DIVERGENCE.md"))
    print(f"{os.path.basename(dossier)} : {r['verdict']}")
    for d, h, t in v.journal:
        print(f"  voyageur {d} {h} : {t}")
    for p, x in sorted(r["premier_fait"].items(), key=lambda kv: (kv[1]["date"], kv[1]["heure"])):
        print(f"  {p}{' (cascade)' if p in r['cascade'] else ''} : {x['date']} {x['heure']} {x['genre']} ({x['detail'][:90]})")


if __name__ == "__main__":
    main()
