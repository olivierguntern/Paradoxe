"""Fait vivre plusieurs habitants ensemble, pas à pas, jour après jour.

Usage :
  python3 outils/simuler_quartier.py 2010-03-08 2010-03-14 --personnages robert-chazal josiane-chazal --dossier data/quartier

Les journées de chacun sont écrites dans <dossier>/<personnage>/. Chaque jour
part de l'état final de la veille (ou de la fiche pour le premier jour).
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moteur
from fiches import charger
from quartier import Quartier

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def simuler(personnages, debut, fin, dossier, voyageur=None, bavard=True):
    """Fait vivre le quartier jour après jour ; avec un voyageur, c'est le monde joué."""
    fiches = {p: charger(p) for p in personnages}
    catalogue = json.load(open(os.path.join(RACINE, "data", "monde", "actions.json"), encoding="utf-8"))
    for p in fiches:
        os.makedirs(os.path.join(dossier, p), exist_ok=True)
    d, fin = datetime.date.fromisoformat(debut), datetime.date.fromisoformat(fin)
    while d <= fin:
        date, veille = d.isoformat(), (d - datetime.timedelta(days=1)).isoformat()
        etats = {p: moteur.etat_initial_depuis_fiche(f) if date == f["meta"]["periode"]["debut"][:10]
                 else moteur.etat_depuis_veille(os.path.join(dossier, p, f"{veille}.json")) for p, f in fiches.items()}
        q = Quartier(fiches, catalogue, date, etats, voyageur)
        try:
            res = q.vivre()
        except moteur.Incoherence as e:
            sys.exit(f"{date} : incohérence : {e}")
        for p, (steps, etat_final, stats) in res.items():
            h = q.H[p]
            moteur.ecrire(fiches[p], h.j, steps, etats[p], etat_final, stats,
                          os.path.join(dossier, p, f"{date}.json"), os.path.join(dossier, p, f"{date}.md"))
            if bavard:
                print(f"{date} {p} : extinction {h.j.extinction} ; " + " ".join(x.replace("**", "") for x in h.j.bilan[1:]))
                for x in h.decisions:
                    if "n'est pas là" in x:
                        print("   ", x)
        d += datetime.timedelta(days=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("debut")
    ap.add_argument("fin")
    ap.add_argument("--personnages", nargs="+", required=True)
    ap.add_argument("--dossier", required=True)
    a = ap.parse_args()
    simuler(a.personnages, a.debut, a.fin, a.dossier)


if __name__ == "__main__":
    main()
