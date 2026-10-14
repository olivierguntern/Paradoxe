"""Fait vivre le personnage par l'agent autonome, jour après jour.

Usage :
  python3 outils/simuler_agent.py 2010-03-08 2010-03-14 --dossier data/timelines/thomas-berthier
  python3 outils/simuler_agent.py 2010-03-08 2010-03-10 --dossier data/simulations/thomas-berthier --sans-courses

Chaque jour part de l'état final de la veille, lu dans --dossier (ou de la
fiche pour le premier jour de la période). Avec --memoire, l'état physique
vient de --dossier et la mémoire de l'agent (avancement des travaux,
habitudes…) vient de la veille simulée dans --memoire. Avec --scenario, les
perturbations du fichier (changements faits à l'insu du personnage) sont
appliquées à leur heure :
  python3 outils/simuler_agent.py 2010-03-08 2010-03-09 --dossier data/scenarios/cles-deplacees --scenario data/scenarios/cles-deplacees.json
"""
import argparse
import datetime
import json
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moteur
from agent import Agent
from agent_epicier import AgentEpicier

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("debut")
    ap.add_argument("fin")
    ap.add_argument("--personnage", default="thomas-berthier")
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--memoire")
    ap.add_argument("--sans-courses", action="store_true", help="sans les courses à l'épicerie (pour rejouer les journées de référence)")
    ap.add_argument("--scenario", help="fichier de perturbations faites à l'insu du personnage (data/scenarios/)")
    a = ap.parse_args()
    perturbations = json.load(open(a.scenario, encoding="utf-8"))["perturbations"] if a.scenario else None
    fiche = json.load(open(os.path.join(RACINE, "data", "personnages", f"{a.personnage}.json"), encoding="utf-8"))
    dossier_agent = os.path.join(RACINE, "data", "agents", a.personnage)
    os.makedirs(a.dossier, exist_ok=True)
    d = datetime.date.fromisoformat(a.debut)
    fin = datetime.date.fromisoformat(a.fin)
    while d <= fin:
        date = d.isoformat()
        veille = (d - datetime.timedelta(days=1)).isoformat()
        if date == fiche["meta"]["periode"]["debut"][:10]:
            etat = moteur.etat_initial_depuis_fiche(fiche)
        else:
            etat = moteur.etat_depuis_veille(os.path.join(a.dossier, f"{veille}.json"))
            if a.memoire:
                etat["agent"] = moteur.etat_depuis_veille(os.path.join(a.memoire, f"{veille}.json"))["agent"]
        type_agent = json.load(open(os.path.join(dossier_agent, "regles.json"), encoding="utf-8")).get("type")
        if type_agent == "commerce":
            if perturbations:
                sys.exit("les perturbations ne s'appliquent pas encore à l'agent du commerçant")
            agent = AgentEpicier(fiche, dossier_agent, date, etat)
        else:
            agent = Agent(fiche, dossier_agent, date, etat, perturbations)
        agent.sans_courses = a.sans_courses
        try:
            steps, etat_final, stats = agent.vivre()
        except moteur.Incoherence as e:
            sys.exit(f"{date} : incohérence : {e}")
        moteur.ecrire(fiche, agent.j, steps, etat, etat_final, stats,
                      os.path.join(a.dossier, f"{date}.json"), os.path.join(a.dossier, f"{date}.md"))
        print(f"{date} : {len(steps)} pas ; extinction {agent.j.extinction}, endormissement {agent.j.endormissement} min ; "
              f"{len(agent.decisions)} décisions notables")
        d += datetime.timedelta(days=1)


if __name__ == "__main__":
    main()
