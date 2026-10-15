"""Prépare les données de la page du quartier (vue/quartier.js).

Usage : python3 outils/exporter_quartier.py [--dossier data/quartier]

Pour chaque habitant et chaque pas de la semaine : où il est (chez lui, chez
quelqu'un, à la boutique, dehors, en voiture, endormi), le lieu et la pièce,
l'activité, l'action, avec qui, et ses besoins. Y joint les alertes du
contrôle de cohérence (outils/controler_quartier.py), qui écrit aussi
<dossier>/CONTROLE.md.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from controler_quartier import controler, ecrire
from fiches import charger

sys.stdout.reconfigure(encoding="utf-8")
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES = ["endormi", "chez lui", "chez quelqu'un", "commerce", "dehors", "en voiture"]
BESOINS = ["faim", "soif", "energie", "hygiene", "toilettes", "social", "detente"]


class Textes:
    def __init__(self):
        self.liste, self.index = [], {}

    def __call__(self, t):
        if t not in self.index:
            self.index[t] = len(self.liste)
            self.liste.append(t)
        return self.index[t]


def categorie(s, chez_lui, commerces):
    if "phase_sommeil" in s:
        return 0
    if s["lieu"] == "exterieur":
        return 4
    if s["lieu"] in commerces:
        return 3
    if "voiture" in s["lieu"] or s["piece"] == "Kangoo":
        return 5
    if s["lieu"] in chez_lui:
        return 1
    return 2


def exporter(dossier, sortie):
    habitants, dates, alertes = controler(dossier)
    ecrire(dossier, habitants, dates, alertes)
    fiches = {p: charger(p) for p in habitants}
    commerces = {F["commerce"]["id"] for F in fiches.values() if F.get("commerce")}
    T = Textes()
    donnees = {"dates": dates, "pas_par_jour": 288, "categories": CATEGORIES, "besoins": BESOINS, "habitants": [], "alertes": alertes}
    for p in habitants:
        F = fiches[p]
        sites = F["domicile"]["plan"].get("lieux_des_sites", {})
        logements = F["domicile"]["plan"].get("logements_des_sites", {})
        premier = (F.get("logements") or [None])[0]
        chez_lui = {"domicile"} | {premier} | {lieu for s, lieu in sites.items() if logements.get(s, s) == premier or s == "maison"}
        pas = []
        for d in dates:
            for s in json.load(open(os.path.join(dossier, p, f"{d}.json"), encoding="utf-8"))["pas"]:
                ou = s["piece"] if s["lieu"] in ("domicile", s["piece"]) else f"{s['piece']} ({s['lieu']})"
                pas.append([categorie(s, chez_lui, commerces), T(ou), T(s["activite"]), T(s["action"]), T(", ".join(s.get("ensemble", []))),
                            [round(s["besoins"].get(n, 0)) for n in BESOINS]])
        donnees["habitants"].append({"id": p, "prenom": F["identite"]["prenom"], "nom": F["identite"].get("nom", ""),
                                     "seuils": [F["besoins"][n]["seuil_alerte"] if n in F["besoins"] else 0 for n in BESOINS], "pas": pas})
    donnees["textes"] = T.liste
    with open(sortie, "w", encoding="utf-8") as f:
        f.write("window.QUARTIER = ")
        json.dump(donnees, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"{len(habitants)} habitants, {len(alertes)} alerte(s), {len(T.liste)} textes → {os.path.relpath(sortie, RACINE)} ({os.path.getsize(sortie) // 1024} Ko)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=os.path.join(RACINE, "data", "quartier"))
    ap.add_argument("--sortie", default=os.path.join(RACINE, "vue", "quartier.js"))
    a = ap.parse_args()
    exporter(a.dossier, a.sortie)
