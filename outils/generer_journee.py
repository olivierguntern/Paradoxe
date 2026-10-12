"""Génère la timeline d'une journée.

Usage : python3 outils/generer_journee.py 2010-03-09 [--personnage thomas-berthier]

Le contenu rédigé est lu dans outils/journees/<date>.py. L'état de départ est
l'état final de la veille (data/references/<personnage>/<veille>.json) ou, pour
le premier jour de la période, l'état initial de la fiche.

Les journées rédigées à la main servent de référence pour valider l'agent
autonome (outils/comparer_journees.py) ; la semaine officielle est vécue par
l'agent (data/timelines/).
"""
import argparse
import datetime
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json

import moteur

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--personnage", default="thomas-berthier")
    a = ap.parse_args()

    fiche = json.load(open(os.path.join(RACINE, "data", "personnages", f"{a.personnage}.json")))
    dossier = os.path.join(RACINE, "data", "references", a.personnage)
    os.makedirs(dossier, exist_ok=True)

    debut = fiche["meta"]["periode"]["debut"][:10]
    if a.date == debut:
        etat = moteur.etat_initial_depuis_fiche(fiche)
    else:
        veille = (datetime.date.fromisoformat(a.date) - datetime.timedelta(days=1)).isoformat()
        chemin_veille = os.path.join(dossier, f"{veille}.json")
        if not os.path.exists(chemin_veille):
            sys.exit(f"La veille ({veille}) doit être générée avant le {a.date}.")
        etat = moteur.etat_depuis_veille(chemin_veille)

    spec = importlib.util.spec_from_file_location("journee", os.path.join(RACINE, "outils", "journees", f"{a.date}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    j = module.rediger()

    try:
        steps, etat_final, stats = moteur.simuler(fiche, j, etat)
    except moteur.Incoherence as e:
        sys.exit(f"Incohérence : {e}")
    moteur.ecrire(fiche, j, steps, etat, etat_final, stats,
                  os.path.join(dossier, f"{a.date}.json"), os.path.join(dossier, f"{a.date}.md"))
    d = stats
    print(f"{a.date} : {len(steps)} pas ; {round(d['entre_pieces_m'] + d['dans_les_pieces_m'] + d['exterieur_m'])} m parcourus, "
          f"{d['marches']} marches ; endormissement en {d['endormissement_min']} min (anxiété {d['anxiete_extinction']}, excitation {d['excitation_extinction']})")


if __name__ == "__main__":
    main()
