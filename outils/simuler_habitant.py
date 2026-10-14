"""Fait vivre un personnage par l'habitant générique, jour après jour.

Usage :
  python3 outils/simuler_habitant.py 2010-03-08 2010-03-08 --dossier data/generique/thomas-berthier
  python3 outils/comparer_journees.py data/references/thomas-berthier/2010-03-08.json data/generique/thomas-berthier/2010-03-08.json

Chaque jour part de l'état final de la veille, lu dans --dossier (ou de la
fiche pour le premier jour de la période).
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moteur
from habitant import Habitant

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("debut")
    ap.add_argument("fin")
    ap.add_argument("--personnage", default="thomas-berthier")
    ap.add_argument("--dossier", required=True)
    a = ap.parse_args()
    fiche = json.load(open(os.path.join(RACINE, "data", "personnages", f"{a.personnage}.json"), encoding="utf-8"))
    catalogue = json.load(open(os.path.join(RACINE, "data", "monde", "actions.json"), encoding="utf-8"))
    os.makedirs(a.dossier, exist_ok=True)
    d, fin = datetime.date.fromisoformat(a.debut), datetime.date.fromisoformat(a.fin)
    while d <= fin:
        date = d.isoformat()
        if date == fiche["meta"]["periode"]["debut"][:10]:
            etat = moteur.etat_initial_depuis_fiche(fiche)
        else:
            etat = moteur.etat_depuis_veille(os.path.join(a.dossier, f"{(d - datetime.timedelta(days=1)).isoformat()}.json"))
        h = Habitant(fiche, catalogue, date, etat)
        try:
            steps, etat_final, stats = h.vivre()
        except moteur.Incoherence as e:
            sys.exit(f"{date} : incohérence : {e}")
        moteur.ecrire(fiche, h.j, steps, etat, etat_final, stats,
                      os.path.join(a.dossier, f"{date}.json"), os.path.join(a.dossier, f"{date}.md"))
        print(f"{date} : {len(steps)} pas ; extinction {h.j.extinction}, endormissement {h.j.endormissement} min ; {len(h.decisions)} décisions")
        d += datetime.timedelta(days=1)


if __name__ == "__main__":
    main()
