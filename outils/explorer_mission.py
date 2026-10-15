"""Explore les variantes d'un plan du voyageur : la mission est-elle trop facile, trop difficile ?

Usage : python3 outils/explorer_mission.py data/voyageur/mission-soignee.json [--processus 8]

À partir d'un scénario qui porte une mission, essaie des variantes du plan :
- decale : tout le plan avancé ou retardé (de 4 h plus tôt à 4 h plus tard, par demi-heures) ;
- geste : une seule intervention décalée (une heure ou une demi-heure, plus tôt ou plus tard),
  sans qu'elle chevauche ses voisines ;
- sans : une intervention retirée ;
- jour : tout le plan un autre jour de la semaine, aux mêmes heures.
Chaque variante est jouée comme une partie (les jours qui précèdent la première
intervention sont ceux du monde de référence) ; le rapport dit, pour chacune, le
résultat de la mission, le verdict et ce qui a trahi le voyageur (le premier
habitant qui a remarqué quelque chose, ou le premier geste impossible).

Le rapport est écrit dans data/missions/<mission>-exploration.md.
"""
import argparse
import copy
import datetime
import json
import os
import shutil
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from divergence import comparer_mondes
from moteur import hm, idx
from simuler_quartier import simuler
from simuler_voyageur import evaluer_mission
from voyageur import Voyageur

sys.stdout.reconfigure(encoding="utf-8")
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE = os.path.join(RACINE, "data", "quartier")
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


# ------------------------------------------------------------------ temps absolu (minutes depuis le début de la semaine)
def absolu(x, debut):
    return (datetime.date.fromisoformat(x["date"]) - debut).days * 1440 + idx(x["heure"]) * 5


def placer(x, t, debut):
    j, m = divmod(t, 1440)
    return dict(x, date=(debut + datetime.timedelta(days=j)).isoformat(), heure=hm(m // 5))


def duree(x, G):
    if x["type"] == "geste":
        return x.get("duree_minutes", G[x["geste"]]["duree"])
    return x.get("duree_minutes", 5) if x["type"] in ("retenir", "passer") else 5


def variantes(sc, debut, nb_jours, G):
    """(famille, libellé, scénario) pour chaque variante du plan."""
    I = sc["interventions"]
    T = [absolu(x, debut) for x in I]
    out = []
    def avec(interventions):
        s = copy.deepcopy(sc)
        s["interventions"] = interventions
        return s
    for d in range(-240, 241, 30):
        if d:
            out.append(("decale", f"tout le plan {'+' if d > 0 else '−'}{abs(d) // 60} h {abs(d) % 60:02d}".replace(" h 00", " h"),
                        avec([placer(x, t + d, debut) for x, t in zip(I, T)])))
    for n, x in enumerate(I):
        nom = x.get("geste") or x["type"]
        for d in (-60, -30, 30, 60):
            t = T[n] + d
            # sans chevaucher l'intervention d'avant ni celle d'après (le voyageur ne fait qu'une chose à la fois)
            if n and t < T[n - 1] + duree(I[n - 1], G) and T[n - 1] < T[n]:
                continue
            if n + 1 < len(I) and t + duree(x, G) > T[n + 1] and T[n + 1] > T[n]:
                continue
            out.append(("geste", f"{nom} ({x['date'][8:]} {x['heure']}) {'+' if d > 0 else '−'}{abs(d)} min",
                        avec([placer(y, t if k == n else T[k], debut) for k, y in enumerate(I)])))
    for n, x in enumerate(I):
        out.append(("sans", f"sans {x.get('geste') or x['type']} ({x['date'][8:]} {x['heure']})", avec([y for k, y in enumerate(I) if k != n])))
    premier = min(T) // 1440
    for j in range(nb_jours):
        if j != premier:
            out.append(("jour", f"le {JOURS[(debut + datetime.timedelta(days=j)).weekday()]}", avec([placer(x, t + (j - premier) * 1440, debut) for x, t in zip(I, T)])))
    return out


# ------------------------------------------------------------------ une partie
def jouer(args):
    """Joue une variante ; renvoie son résultat (jamais d'exception : une variante impossible le dit)."""
    famille, libelle, sc, habitants, dates = args
    if not sc["interventions"]:
        return dict(famille=famille, libelle=libelle, resultat="—", verdict="aucune intervention", trahi="")
    dossier = tempfile.mkdtemp(prefix="exploration-")
    try:
        try:
            v = Voyageur(copy.deepcopy(sc))
        except ValueError as e:
            return dict(famille=famille, libelle=libelle, resultat="impossible", verdict=str(e), trahi="")
        premiere = min(x["date"] for x in sc["interventions"])
        if premiere > dates[-1]:
            return dict(famille=famille, libelle=libelle, resultat="impossible", verdict="après la fin de la semaine", trahi="")
        for p in habitants:
            os.makedirs(os.path.join(dossier, p))
            for d in dates:
                if d < premiere:
                    shutil.copy(os.path.join(REFERENCE, p, d + ".json"), os.path.join(dossier, p, d + ".json"))
        try:
            simuler(habitants, max(premiere, dates[0]), dates[-1], dossier, v, bavard=False)
        except SystemExit as e:
            return dict(famille=famille, libelle=libelle, resultat="incohérence", verdict=str(e), trahi="")
        I = v.I
        for x in I:
            if x["type"] == "geste":
                x["_duree"] = v.duree(x)
        r = comparer_mondes(REFERENCE, dossier, v.cibles(), I)
        m = evaluer_mission(sc["mission"], v, r["verdict"]) if sc.get("mission") else None
        trahi = next((f"{d[8:]} {h} : {t}" for d, h, t in v.journal if " remarque : " in t or "ne peut pas" in t or "a appris de" in t), "")
        return dict(famille=famille, libelle=libelle, resultat=m["resultat"] if m else "—", verdict=r["verdict"], trahi=trahi,
                    avenir=(m.get("avenir") or {}).get("titre", "") if m else "")
    finally:
        shutil.rmtree(dossier, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--processus", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    a = ap.parse_args()
    sc = json.load(open(a.scenario, encoding="utf-8"))
    nom = os.path.splitext(os.path.basename(a.scenario))[0]
    habitants = sorted(d for d in os.listdir(REFERENCE) if os.path.isdir(os.path.join(REFERENCE, d)))
    dates = sorted(f[:-5] for f in os.listdir(os.path.join(REFERENCE, habitants[0])) if f.endswith(".json"))
    debut = datetime.date.fromisoformat(dates[0])
    G = json.load(open(os.path.join(RACINE, "data", "monde", "gestes.json"), encoding="utf-8"))["gestes"]
    V = [("plan", "le plan tel quel", sc)] + variantes(sc, debut, len(dates), G)
    print(f"{nom} : {len(V)} parties, {a.processus} à la fois…", flush=True)
    with ProcessPoolExecutor(a.processus) as ex:
        R = list(ex.map(jouer, [(f, l, s, habitants, dates) for f, l, s in V]))
    ecrire(nom, sc, R)


def ecrire(nom, sc, R):
    reussies = [r for r in R if r["resultat"].startswith("réussie")]
    parfaites = [r for r in R if r["resultat"] == "réussie, parfaitement"]
    jouables = [r for r in R if r["resultat"] not in ("impossible", "incohérence", "—")]
    L = [f"# Exploration de « {nom} »", "", sc.get("description", ""), "",
         f"**{len(jouables)} variantes jouées : {len(reussies)} réussies, dont {len(parfaites)} parfaitement ; {len(jouables) - len(reussies)} échouées.**"
         + (f" ({len(R) - len(jouables)} impossibles.)" if len(R) > len(jouables) else ""), "",
         "Chaque variante change une seule chose au plan. « Trahi par » : le premier habitant qui a remarqué quelque chose, ou le premier geste impossible.", ""]
    familles = {"plan": "Le plan", "decale": "Tout le plan décalé", "geste": "Une intervention décalée", "sans": "Une intervention en moins", "jour": "Un autre jour"}
    for f, titre in familles.items():
        G = [r for r in R if r["famille"] == f]
        if not G:
            continue
        ok = sum(1 for r in G if r["resultat"].startswith("réussie"))
        L += [f"## {titre} ({ok} sur {len(G)} réussies)", "", "| Variante | Mission | Verdict | Trahi par |", "|---|---|---|---|"]
        for r in G:
            L.append(f"| {r['libelle']} | {r['resultat']} | {r['verdict'][:90]} | {r['trahi'][:110]} |")
        L.append("")
    sortie = os.path.join(RACINE, "data", "missions", f"{sc.get('mission', 'sans-mission')}-exploration-{nom}.md")
    open(sortie, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"{len(jouables)} jouées : {len(reussies)} réussies ({len(parfaites)} parfaitement) → {os.path.relpath(sortie, RACINE)}")
    for f, titre in familles.items():
        G = [r for r in R if r["famille"] == f]
        if G:
            print(f"  {titre} : {sum(1 for r in G if r['resultat'].startswith('réussie'))} / {len(G)}")


if __name__ == "__main__":
    main()
