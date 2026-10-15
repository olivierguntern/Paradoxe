"""Prépare les données de la page de divergence (vue/divergence.js).

Usage : python3 outils/exporter_divergence.py [--reference data/quartier]

Pour chaque scénario du voyageur (data/voyageur/<nom>.json), lit le monde joué
(data/voyageur/<nom>/, rejoué par outils/simuler_voyageur.py s'il manque) et
son rapport (divergence.json). La page montre, pas à pas, ce que fait chaque
habitant dans le monde de référence et dans le monde joué, les faits
différents (épisodes) et la chaîne de leurs causes.

Le monde de référence est écrit une seule fois ; chaque scénario n'écrit que
les pas qui en diffèrent. Les textes sont rangés dans une table commune.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAS = 288


class Textes:
    def __init__(self):
        self.liste, self.index = [], {}

    def __call__(self, t):
        if t not in self.index:
            self.index[t] = len(self.liste)
            self.liste.append(t)
        return self.index[t]


def journees(dossier, p, dates):
    return [json.load(open(os.path.join(dossier, p, f"{d}.json"), encoding="utf-8")) for d in dates]


def etat(s):
    """Ce que la page montre d'un pas : endroit, activité, action, personnes avec qui il est."""
    lieu = s["piece"] if s["lieu"] in ("domicile", s["piece"]) else f"{s['piece']} ({s['lieu']})"
    return lieu, s["activite"], s["action"], ", ".join(s.get("ensemble", []))


def numero(dates, date, heure):
    return dates.index(date) * PAS + (int(heure[:2]) * 60 + int(heure[3:])) // 5


def exporter(reference, sortie):
    T = Textes()
    habitants = sorted(d for d in os.listdir(reference) if os.path.isdir(os.path.join(reference, d)))
    dates = sorted(f[:-5] for f in os.listdir(os.path.join(reference, habitants[0])) if f.endswith(".json"))
    prenoms = {p: json.load(open(os.path.join(RACINE, "data", "personnages", f"{p}.json"), encoding="utf-8"))["identite"]["prenom"] for p in habitants}
    ref = {p: [etat(s) for J in journees(reference, p, dates) for s in J["pas"]] for p in habitants}
    donnees = {"habitants": [{"id": p, "prenom": prenoms[p]} for p in habitants], "dates": dates, "pas_par_jour": PAS,
               "reference": {p: [[T(x[0]), T(x[1]), T(x[2]), T(x[3])] for x in ref[p]] for p in habitants}, "scenarios": []}
    for chemin in sorted(glob.glob(os.path.join(RACINE, "data", "voyageur", "*.json"))):
        nom = os.path.splitext(os.path.basename(chemin))[0]
        dossier = os.path.splitext(chemin)[0]
        if not all(os.path.exists(os.path.join(dossier, p, f"{dates[-1]}.json")) for p in habitants):
            print(f"{nom} : monde joué absent, simulation…")
            subprocess.run([sys.executable, os.path.join(RACINE, "outils", "simuler_voyageur.py"), chemin, "--reference", reference], check=True)
        sc = json.load(open(chemin, encoding="utf-8"))
        r = json.load(open(os.path.join(dossier, "divergence.json"), encoding="utf-8"))
        joue = {}
        for p in habitants:
            diff = {}
            for k, x in enumerate(etat(s) for J in journees(dossier, p, dates) for s in J["pas"]):
                if x != ref[p][k]:
                    diff[k] = [T(x[0]), T(x[1]), T(x[2]), T(x[3])]
            joue[p] = diff
        faits = [{"id": n["id"], "habitant": n["habitant"], "genre": n["genre"], "detail": n["detail"],
                  "debut": numero(dates, n["date"], n["heure"]), "fin": numero(dates, n["fin_date"], n["fin_heure"]),
                  "cause": n["cause"], "via": n.get("via"), "supposee": n["supposee"]} for n in r["causes"]["faits"]]
        racines = [{"id": v["id"], "pas": numero(dates, v["date"], v["heure"]), "fin": dates.index(v["date"]) * PAS + v["fin"],
                    "type": v["type"], "habitant": v["habitant"], "texte": v["texte"]} for v in r["causes"]["interventions"]]
        donnees["scenarios"].append({
            "id": nom, "description": sc.get("description", ""), "attendu": sc.get("attendu", ""), "porte": sc.get("porte", []),
            "verdict": r["verdict"], "touches": r["touches"], "cascade": r["cascade"], "cibles": r["cibles"],
            "voyageur": r.get("voyageur", []), "racines": racines, "faits": faits, "joue": joue,
            "heures": [h["faits"] for h in r["heures"]], "mission": r.get("mission")})
        print(f"{nom} : {len(faits)} faits, {sum(len(v) for v in joue.values())} pas différents — {r['verdict']}")
    donnees["textes"] = T.liste
    with open(sortie, "w", encoding="utf-8") as f:
        f.write("window.DIVERGENCE = ")
        json.dump(donnees, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"{len(donnees['scenarios'])} scénarios, {len(T.liste)} textes → {os.path.relpath(sortie, RACINE)} ({os.path.getsize(sortie) // 1024} Ko)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", default=os.path.join(RACINE, "data", "quartier"))
    ap.add_argument("--sortie", default=os.path.join(RACINE, "vue", "divergence.js"))
    a = ap.parse_args()
    exporter(a.reference, a.sortie)
