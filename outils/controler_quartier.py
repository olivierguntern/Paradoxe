"""Contrôle de cohérence des journées du quartier.

Usage : python3 outils/controler_quartier.py [--dossier data/quartier]

Relit les journées de chaque habitant et signale ce qui ne tient pas :
- une même pièce de son logement notée dans deux lieux différents ;
- un changement de lieu sans trajet (il passe d'un logement ou d'un lieu à un
  autre d'un pas à l'autre, sans marcher, rouler ni sortir) ;
- une rencontre à sens unique (A est avec B, mais B n'est pas avec A) ;
- un besoin sous son seuil d'alerte, éveillé, plus d'une heure d'affilée ;
- une nuit de moins de six heures de sommeil ;
- pour un commerçant : sa boutique ouverte (horaires de sa fiche) sans lui.

Écrit <dossier>/CONTROLE.md et renvoie les alertes (pour la page du quartier,
outils/exporter_quartier.py).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fiches import charger
from moteur import hm, idx

sys.stdout.reconfigure(encoding="utf-8")
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTERIEURS = ("exterieur",)


def en_route(s):
    """Le pas comprend-il un trajet (à pied, en voiture, une sortie ou un retour) ?"""
    d = s.get("deplacement") or {}
    return bool(d.get("parcours") or d.get("escalier") or s["lieu"] in EXTERIEURS or s["posture"] in ("en marche", "en course")
                or "voiture" in s["piece"].lower() or s["piece"] in ("Kangoo",))


def controler(dossier):
    habitants = sorted(d for d in os.listdir(dossier) if os.path.isdir(os.path.join(dossier, d)))
    dates = sorted(f[:-5] for f in os.listdir(os.path.join(dossier, habitants[0])) if f.endswith(".json"))
    fiches = {p: charger(p) for p in habitants}
    J = {p: {d: json.load(open(os.path.join(dossier, p, f"{d}.json"), encoding="utf-8")) for d in dates} for p in habitants}
    alertes = []

    def alerte(p, date, k, genre, texte):
        alertes.append({"habitant": p, "date": date, "pas": k, "heure": hm(k), "genre": genre, "texte": texte})

    for p in habitants:
        F = fiches[p]
        maison = {pc["id"] for pc in F["domicile"]["pieces"]}
        seuils = {n: b["seuil_alerte"] for n, b in F["besoins"].items()}
        lieux_piece = {}
        sommeil_nuit = 0
        for date in dates:
            pas = J[p][date]["pas"]
            for k, s in enumerate(pas):
                if s["piece"] in maison:
                    lieux_piece.setdefault(s["piece"], {}).setdefault(s["lieu"], (date, k))
                prec = pas[k - 1] if k else None
                if prec and prec["lieu"] != s["lieu"] and not en_route(s) and not en_route(prec):
                    alerte(p, date, k, "téléportation", f"de {prec['piece']} ({prec['lieu']}) à {s['piece']} ({s['lieu']}) sans trajet")
            # besoins sous le seuil, éveillé, plus d'une heure d'affilée
            for n, seuil in seuils.items():
                if n not in pas[0]["besoins"]:
                    continue
                run = 0
                for k, s in enumerate(pas):
                    if "phase_sommeil" not in s and s["besoins"][n] < seuil:
                        run += 1
                        if run == 13:
                            alerte(p, date, k - 12, "besoin", f"{n} sous son seuil d'alerte ({seuil}) depuis plus d'une heure, éveillé ({round(s['besoins'][n], 1)})")
                    else:
                        run = 0
            # sommeil : de midi à midi
            sommeil_nuit += sum(1 for s in pas[:144] if "phase_sommeil" in s)
            if date != dates[0] and sommeil_nuit * 5 < 360:
                alerte(p, date, 0, "sommeil", f"nuit de {sommeil_nuit * 5 // 60} h {sommeil_nuit * 5 % 60:02d} seulement")
            sommeil_nuit = sum(1 for s in pas[144:] if "phase_sommeil" in s)
            # boutique ouverte sans le commerçant
            C = F.get("commerce")
            if C:
                jour = J[p][date]["meta"]["jour"]
                absent = 0
                for a, b in C.get("horaires", {}).get(jour, []):
                    for k in range(idx(a), idx(b)):
                        if pas[k]["lieu"] != C["id"]:
                            absent += 1
                            if absent == 4:
                                alerte(p, date, k - 3, "boutique", f"{C['nom']} ouverte, mais il n'y est pas depuis 20 minutes ({pas[k]['piece']})")
                        else:
                            absent = 0
        for piece, lieux in lieux_piece.items():
            if len(lieux) > 1:
                (d0, k0) = sorted(lieux.values())[0]
                alerte(p, d0, k0, "lieu", f"la pièce {piece} est notée dans plusieurs lieux : {', '.join(sorted(lieux))}")
    # rencontres réciproques
    prenoms = {fiches[p]["identite"]["prenom"]: p for p in habitants}
    for date in dates:
        for k in range(len(J[habitants[0]][date]["pas"])):
            for p in habitants:
                for nom in J[p][date]["pas"][k].get("ensemble", []):
                    q = prenoms.get(nom)
                    if q and fiches[p]["identite"]["prenom"] not in J[q][date]["pas"][k].get("ensemble", []):
                        alerte(p, date, k, "rencontre", f"avec {nom}, mais {nom} n'est pas avec lui/elle")
    return habitants, dates, alertes


def ecrire(dossier, habitants, dates, alertes):
    L = ["# Contrôle du quartier", "", f"{len(alertes)} alerte(s) sur {len(habitants)} habitants et {len(dates)} jours.", ""]
    par = {}
    for a in alertes:
        par.setdefault(a["genre"], []).append(a)
    for g, xs in sorted(par.items()):
        L += [f"## {g} ({len(xs)})", ""]
        L += [f"- {a['habitant']}, {a['date']} {a['heure']} : {a['texte']}" for a in xs[:40]]
        if len(xs) > 40:
            L.append(f"- … et {len(xs) - 40} autres")
        L.append("")
    open(os.path.join(dossier, "CONTROLE.md"), "w", encoding="utf-8").write("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=os.path.join(RACINE, "data", "quartier"))
    a = ap.parse_args()
    h, d, al = controler(a.dossier)
    ecrire(a.dossier, h, d, al)
    par = {}
    for x in al:
        par[x["genre"]] = par.get(x["genre"], 0) + 1
    print(f"{len(al)} alerte(s) : " + ", ".join(f"{g} {n}" for g, n in sorted(par.items())))
