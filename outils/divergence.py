"""Divergence entre le monde de référence et le monde joué (avec le voyageur).

Usage : python3 outils/divergence.py data/quartier data/voyageur/<nom> [--cibles thomas-berthier ...]

Les deux mondes sont comparés pas à pas, habitant par habitant, en deux
niveaux (CONCEPTION.md, « Mesure envisagée ») :
- les faits, comptés dans la divergence : l'endroit où il est, l'activité, les
  personnes avec qui il est, la place de chaque objet, ce qu'il achète, ce
  qu'il a appris, les anachronismes qu'il a remarqués ou dont il a entendu
  parler ;
- les détails, tolérés : besoins, émotions, quantités en stock (maison et
  magasin), argent. Ils sont mesurés, pas comptés.

La divergence suit, heure par heure, le nombre de faits différents (chacun
compté une fois dans l'heure, même s'il dure) et le nombre d'habitants
touchés. Un habitant touché sans être visé par une
intervention ni témoin d'un anachronisme l'est par cascade. Chaque fait différent reçoit sa cause (classe Causes) : l'arbre remonte une
cascade jusqu'à l'intervention du voyageur. Le verdict, selon les seuils de
data/monde/paradoxe.json : aucune divergence, divergence absorbée (plus aucun
fait différent à la fin), persistante, en cascade, ou paradoxe.
"""
import datetime
import json
import os
import sys

from comparer_journees import positions_par_pas
from fiches import MONDE, RACINE, lire
from moteur import idx

GESTES = lire(os.path.join(MONDE, "gestes.json"))["gestes"]

sys.stdout.reconfigure(encoding="utf-8")


def appris_au_pas(j, heure):
    """Ce que l'habitant a appris jusqu'à ce pas (mémoire gardée d'un jour à l'autre) : qui le lui a dit, et quoi ;
    la même chose apprise à un autre moment n'est pas une différence."""
    date = j["meta"]["date"]
    return {(x["de"], x.get("quoi")) for x in (j["etat_final"].get("habitant") or {}).get("appris", [])
            if (x["date"], x["heure"]) <= (date, heure)}


JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def quand(date, heure=None):
    """« le jeudi 11 mars, entre 18:00 et 19:00 »."""
    d = datetime.date.fromisoformat(date)
    txt = f"le {JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}"
    if heure:
        h = int(heure[:2])
        txt += f", entre {heure} et {(h + 1) % 24:02d}:00"
    return txt


def anomalies_au_pas(j, heure):
    """Les anachronismes qu'il a remarqués ou dont il a entendu parler jusqu'à ce pas : (objet, qui le lui a dit ou None)."""
    date = j["meta"]["date"]
    return {(x["objet"], x.get("par"), x["quoi"]) for x in (j["etat_final"].get("habitant") or {}).get("anomalies", [])
            if (x["date"], x["heure"]) <= (date, heure)}


def faits_du_pas(a, b, pa, pb, ja, jb, infos=None):
    """Faits différents entre deux pas d'un même habitant : liste de (genre, détail). Si infos (dict) est donné, il reçoit
    pour chaque fait ce qui sert à en trouver la cause : personnes concernées, objet, produits, qui a dit quoi."""
    out = []
    infos = {} if infos is None else infos
    infos["_routine"] = b.get("routine")
    if (a["lieu"], a["piece"]) != (b["lieu"], b["piece"]):
        out.append(("lieu", f"{a['piece']} → {b['piece']}"))
    if a["activite"] != b["activite"]:
        out.append(("activité", f"{a['activite']} → {b['activite']}"))
    ea, eb = set(a.get("ensemble", [])), set(b.get("ensemble", []))
    if ea != eb:
        out.append(("rencontre", "; ".join(([f"sans {', '.join(sorted(ea - eb))}"] if ea - eb else []) + ([f"avec {', '.join(sorted(eb - ea))}"] if eb - ea else []))))
        infos[out[-1]] = {"autres": sorted(ea ^ eb)}
    for o in sorted(set(pa[0]) | set(pb[0])):
        if pa[0].get(o) != pb[0].get(o):
            out.append(("objet", f"{o} : {pa[0].get(o)} → {pb[0].get(o)}"))
            infos[out[-1]] = {"objet": o}
    aa = sorted((x["produit"], x["quantite"]) for x in a.get("achats", []))
    ab = sorted((x["produit"], x["quantite"]) for x in b.get("achats", []))
    if aa != ab:
        out.append(("achat", f"{aa} → {ab}"))
        infos[out[-1]] = {"produits": sorted({x[0] for x in set(aa) ^ set(ab)})}
    sa, sb = appris_au_pas(ja, a["heure"]), appris_au_pas(jb, b["heure"])
    for x in sorted(sa ^ sb):
        out.append(("appris", f"{'ne sait pas' if x in sa else 'apprend'} : {x[1]}"))
        infos[out[-1]] = {"de": x[0]}
    sa, sb = anomalies_au_pas(ja, a["heure"]), anomalies_au_pas(jb, b["heure"])
    sources = {(x["objet"], x.get("par"), x["quoi"]): x.get("source") for x in (jb["etat_final"].get("habitant") or {}).get("anomalies", [])}
    for o, par, quoi in sorted(sa ^ sb, key=str):
        if (o, par, quoi) in sa:
            verbe = "ne remarque pas" if par is None else "n'entend pas parler de"
        else:
            verbe = "remarque" if par is None else "entend parler de"
        out.append(("anomalie", f"{verbe} : {quoi}"))
        infos[out[-1]] = {"anomalie": o, "par": par, "quoi": quoi, "source": sources.get((o, par, quoi))}
    return out


def details_du_pas(a, b, pa, pb):
    """Écarts tolérés : besoins et émotions (écart absolu moyen), produits en stock et comptes différents."""
    besoins = sum(abs(a["besoins"][k] - b["besoins"][k]) for k in a["besoins"]) / len(a["besoins"])
    emotions = sum(abs(a["emotions"][k] - b["emotions"][k]) for k in a["emotions"]) / len(a["emotions"])
    stock = sum(pa[1].get(k) != pb[1].get(k) for k in set(pa[1]) | set(pb[1]))
    magasin = sum(pa[2].get(k) != pb[2].get(k) for k in set(pa[2]) | set(pb[2]))
    argent = sum(pa[3].get(k) != pb[3].get(k) for k in set(pa[3]) | set(pb[3]))
    return besoins, emotions, stock, magasin, argent


class Causes:
    """Chaîne des causes : chaque fait différent qui dure forme un épisode (habitant, genre, détail, début, fin), et chaque
    épisode reçoit, quand il commence, la cause la plus directe :
    1. une intervention du voyageur sur cet habitant à ce moment (il le retient, déplace son objet, lui dit quelque chose) ;
       un anachronisme remarqué : l'intervention pendant laquelle le voyageur a été vu ; entendu raconter : celui qui
       l'a raconté ;
    2. une rencontre manquée ou nouvelle avec quelqu'un : ce qui a changé pour l'autre à ce moment (son endroit, son
       activité), sinon pour lui-même ;
    3. quelque chose appris (ou non) de quelqu'un : la dernière rencontre différente avec lui, sinon ce qui a changé
       dans sa journée ;
    4. un achat différent : sa propre journée changée, sinon un achat du voyageur sur ce produit ; un objet pris ou
       laissé autrement : ce qu'il était en train de faire ;
    5. sinon, son propre épisode précédent (la suite de ce qui a déjà changé pour lui) ; à défaut, le dernier fait
       différent du quartier, en lien supposé."""

    ORDRE = ["lieu", "activité", "objet", "achat", "anomalie", "rencontre", "appris"]

    def __init__(self, interventions, prenoms):
        self.prenoms = prenoms                       # habitant -> prénom (les rencontres nomment les gens par leur prénom)
        self.par_prenom = {v: k for k, v in prenoms.items()}
        self.V = []
        for n, x in enumerate(interventions, 1):
            qui = x.get("habitant") or x.get("commerce")
            d = idx(x["heure"])
            texte = {"retenir": f"retient {prenoms.get(qui, qui)} {x.get('duree_minutes', 5)} minutes",
                     "deplacer": f"déplace {x.get('objet')} de {prenoms.get(qui, qui)} vers « {x.get('vers')} »",
                     "acheter": f"achète {x.get('quantite')} × {x.get('produit')} chez {prenoms.get(qui, qui)}",
                     "parler": f"dit à {prenoms.get(qui, qui)} : « {x.get('quoi')} »",
                     "geste": f"{GESTES.get(x.get('geste'), {}).get('nom', x.get('geste'))} ({x.get('_duree', x.get('duree_minutes', ''))} min)",
                     "passer": f"passe dans {x.get('piece') or x.get('lieu') or prenoms.get(qui, qui)}"}.get(x["type"], x["type"])
            self.V.append({"id": f"V{n}", "date": x["date"], "heure": x["heure"], "pas": d,
                           "fin": d + max(1, x.get("duree_minutes", x.get("_duree", 5)) // 5) if x["type"] in ("retenir", "passer", "geste") else d + 1,
                           "type": x["type"], "habitant": qui, "x": x, "texte": texte})
        self.noeuds = []
        self.actifs = {}      # habitant -> {(genre, détail): épisode}
        self.histoire = {}    # habitant -> épisodes dans l'ordre où ils ont commencé

    def pas(self, date, k, heure, faits, infos, besoins=None):
        """faits : habitant -> [(genre, détail)] du pas ; infos : habitant -> {(genre, détail): informations} ;
        besoins : habitant -> écart moyen des besoins à ce pas (un détail, qui peut décaler un geste)."""
        self.besoins = besoins or {}
        for p in set(self.actifs) | set(faits):
            presents = set(faits.get(p, []))
            for cle in [c for c in self.actifs.get(p, {}) if c not in presents]:
                del self.actifs[p][cle]
        nouveaux = [(p, f) for p, fs in faits.items() for f in fs if f not in self.actifs.get(p, {})]
        nouveaux.sort(key=lambda x: self.ORDRE.index(x[1][0]))
        for p, (g, d) in nouveaux:
            n = {"id": f"F{len(self.noeuds) + 1}", "habitant": p, "genre": g, "detail": d, "date": date, "heure": heure,
                 "fin_date": date, "fin_heure": heure, "cause": None, "supposee": False}
            self.via = None
            self.reaction = infos.get(p, {}).get("_routine") == "reaction"
            n["cause"], n["supposee"] = self.cause(p, g, infos.get(p, {}).get((g, d), {}), date, k)
            if self.via:
                n["via"] = self.via
            self.noeuds.append(n)
            self.actifs.setdefault(p, {})[(g, d)] = n
            self.histoire.setdefault(p, []).append(n)
        for p, fs in faits.items():
            for f in fs:
                self.actifs[p][f]["fin_date"], self.actifs[p][f]["fin_heure"] = date, heure

    @staticmethod
    def nombre(n, autre=""):
        """« 1 autre fait », « 3 autres faits »."""
        return f"{n} {autre}fait" if n == 1 else f"{n} {autre.replace('autre ', 'autres ')}faits"

    def noeud(self, nid):
        return self.noeuds[int(nid[1:]) - 1]

    def actif(self, p, genres):
        ns = [n for (g, _), n in self.actifs.get(p, {}).items() if g in genres]
        return min(ns, key=lambda n: ("lieu", "activité", "objet", "achat", "rencontre", "appris").index(n["genre"])) if ns else None

    def recent(self, p, genres=None, avant=None):
        ns = [n for n in self.histoire.get(p, []) if (genres is None or n["genre"] in genres) and n is not avant]
        return ns[-1] if ns else None

    def cause(self, p, g, info, date, k):
        # 1. intervention du voyageur
        for v in self.V:
            if v["date"] != date and v["type"] != "deplacer":
                continue
            if v["type"] == "retenir" and v["habitant"] == p and v["pas"] <= k < v["fin"] and g in ("lieu", "activité"):
                return v["id"], False
            if v["type"] == "deplacer" and v["habitant"] == p and g == "objet" and info.get("objet") == v["x"]["objet"] \
                    and (date, k) >= (v["date"], v["pas"]) and not any(n["genre"] == "objet" and n["detail"].startswith(v["x"]["objet"]) for n in self.histoire.get(p, [])):
                return v["id"], False
            if v["type"] == "parler" and v["habitant"] == p and g == "appris" and info.get("de") == "voyageur":
                return v["id"], False
        # un anachronisme : vu pendant une intervention du voyageur, ou entendu de quelqu'un qui l'a vu ou entendu
        if g == "anomalie":
            if info.get("par") is None:
                v = (next((v for v in self.V if v["id"] == info.get("source")), None)
                     or next((v for v in self.V if v["date"] == date and v["pas"] <= k < v["fin"]), None)
                     or next((v for v in reversed(self.V) if (v["date"], v["pas"]) <= (date, k)), None))
                if v:
                    return v["id"], False
            elif info["par"] in self.prenoms:
                # ce que le conteur a remarqué ou entendu de la même chose, sinon sa dernière anomalie, sinon son dernier fait
                ns = [n for n in reversed(self.histoire.get(info["par"], [])) if n["genre"] == "anomalie"]
                n = next((n for n in ns if n["detail"].endswith(info.get("quoi") or "\0")), None) or (ns[0] if ns else None) or self.recent(info["par"])
                if n:
                    return n["id"], False
        # 2. rencontre
        if g == "rencontre":
            for nom in info.get("autres", []):
                q = self.par_prenom.get(nom)
                n = self.actif(q, ("lieu", "activité")) if q else None
                if n:
                    return n["id"], False
            n = self.actif(p, ("lieu", "activité"))
            if n:
                return n["id"], False
            for nom in info.get("autres", []):
                n = self.recent(self.par_prenom.get(nom), ("lieu", "activité", "objet", "achat"))
                if n:
                    return n["id"], False
        # 3. ce qu'on apprend de quelqu'un
        if g == "appris" and info.get("de") in self.prenoms:
            q, nom = info["de"], self.prenoms[info["de"]]
            n = next((n for n in reversed(self.histoire.get(p, [])) if n["genre"] == "rencontre" and nom in n["detail"]), None) \
                or self.recent(q)
            if n:
                return n["id"], False
        # un objet pris ou laissé autrement : ce qu'il était en train de faire à ce moment
        if g == "objet":
            n = self.actif(p, ("activité",)) or self.actif(p, ("lieu",))
            if n:
                return n["id"], False
        # 4. achat
        if g == "achat":
            n = self.actif(p, ("lieu", "activité"))
            if n:
                return n["id"], False
            for v in self.V:
                if v["type"] == "acheter" and v["date"] == date and v["pas"] <= k and v["x"]["produit"] in info.get("produits", []):
                    return v["id"], False
        # 5. la suite de ce qui a déjà changé pour lui : un endroit ou une activité se rattache au premier changement
        #    de sa journée dont il découle (par ses besoins décalés, si c'est le cas) ; sinon son dernier fait ;
        #    à défaut, le dernier fait du quartier (lien supposé)
        if g in ("lieu", "activité") and self.reaction:
            n = self.recent(p, ("anomalie",))   # une réaction : ce qu'il vient de remarquer
            if n:
                return n["id"], False
        if g in ("lieu", "activité"):
            n = self.recent(p, ("lieu", "activité"))
            while n and n["cause"] and n["cause"].startswith("F") and self.noeud(n["cause"])["habitant"] == p                     and self.noeud(n["cause"])["genre"] in ("lieu", "activité"):
                n = self.noeud(n["cause"])
            if n:
                self.via = "par ses besoins décalés" if self.besoins.get(p, 0) >= 0.5 else None
                return n["id"], False
        n = self.recent(p)
        if n:
            return n["id"], False
        if self.noeuds:
            return self.noeuds[-1]["id"], True
        return None, True

    def arbre(self, limite_enfants=8, profondeur=10):
        """Lignes Markdown de l'arbre des causes, des interventions du voyageur aux derniers faits."""
        enfants = {}
        for n in self.noeuds:
            enfants.setdefault(n["cause"], []).append(n)
        L = []
        def court(date):
            d = datetime.date.fromisoformat(date)
            return f"{JOURS[d.weekday()]} {d.day}"
        def ligne(n, niveau):
            duree = "" if (n["date"], n["heure"]) == (n["fin_date"], n["fin_heure"]) else (
                f", jusqu'à {n['fin_heure']}" if n["fin_date"] == n["date"] else f", jusqu'au {court(n['fin_date'])} {n['fin_heure']}")
            L.append("  " * niveau + f"- **{self.prenoms.get(n['habitant'], n['habitant'])}**, {court(n['date'])} {n['heure']}{duree} — "
                     f"{n['genre']} : {n['detail'][:160]}{' (' + n['via'] + ')' if n.get('via') else ''}{' (lien supposé)' if n['supposee'] else ''}")
            ens = enfants.get(n["id"], [])
            if niveau >= profondeur and ens:
                L.append("  " * (niveau + 1) + f"- … {self.nombre(len(ens))} qui en découle{'nt' if len(ens) > 1 else ''}")
                return
            for e in ens[:limite_enfants]:
                ligne(e, niveau + 1)
            if len(ens) > limite_enfants:
                L.append("  " * (niveau + 1) + f"- … et {self.nombre(len(ens) - limite_enfants, 'autre ')}")
        for v in self.V:
            L.append(f"- **Le voyageur**, {court(v['date'])} {v['heure']} — {v['texte']}")
            for e in enfants.get(v["id"], [])[:limite_enfants]:
                ligne(e, 1)
            if len(enfants.get(v["id"], [])) > limite_enfants:
                L.append(f"  - … et {self.nombre(len(enfants[v['id']]) - limite_enfants, 'autre ')}")
        for e in enfants.get(None, []):
            ligne(e, 0)
        return L


def comparer_mondes(ref, joue, cibles=(), interventions=()):
    S = lire(os.path.join(MONDE, "paradoxe.json"))
    habitants = sorted(d for d in os.listdir(joue) if os.path.isdir(os.path.join(joue, d)))
    dates = sorted(f[:-5] for f in os.listdir(os.path.join(joue, habitants[0])) if f.endswith(".json"))
    heures = []          # (date, heure, faits, habitants touchés)
    premier = {}         # habitant -> premier fait divergent
    par_habitant = {p: {"pas_divergents": 0, "faits": 0} for p in habitants}
    details_fin = {}
    exemples = {}
    distincts = {}       # habitant -> faits différents (genre, détail), chacun compté une fois
    prenoms = {p: lire(os.path.join(RACINE, "data", "personnages", f"{p}.json"))["identite"]["prenom"] for p in habitants}
    causes = Causes(interventions, prenoms)
    for date in dates:
        J = {p: (json.load(open(os.path.join(ref, p, f"{date}.json"), encoding="utf-8")),
                 json.load(open(os.path.join(joue, p, f"{date}.json"), encoding="utf-8"))) for p in habitants}
        P = {p: (positions_par_pas(ja), positions_par_pas(jb)) for p, (ja, jb) in J.items()}
        faits_h, touches_h = set(), set()
        for k in range(len(J[habitants[0]][0]["pas"])):
            faits, touches = 0, set()
            du_pas, infos = {}, {}
            for p in habitants:
                ja, jb = J[p]
                a, b = ja["pas"][k], jb["pas"][k]
                infos[p] = {}
                f = faits_du_pas(a, b, P[p][0][k], P[p][1][k], ja, jb, infos[p])
                if f:
                    du_pas[p] = f
                    faits += len(f)
                    touches.add(p)
                    faits_h |= {(p, g, d) for g, d in f}
                    distincts.setdefault(p, set()).update(f)
                    par_habitant[p]["pas_divergents"] += 1
                    par_habitant[p]["faits"] = len(distincts[p])
                    premier.setdefault(p, {"date": date, "heure": a["heure"], "genre": f[0][0], "detail": f[0][1]})
                    for g, d in f:
                        exemples.setdefault(p, {}).setdefault(g, (date, a["heure"], d))
                if k == len(ja["pas"]) - 1 and date == dates[-1]:
                    details_fin[p] = details_du_pas(a, b, P[p][0][k], P[p][1][k])
            ecarts = {p: sum(abs(J[p][0]["pas"][k]["besoins"][x] - J[p][1]["pas"][k]["besoins"][x]) for x in J[p][0]["pas"][k]["besoins"])
                         / len(J[p][0]["pas"][k]["besoins"]) for p in du_pas}
            causes.pas(date, k, J[habitants[0]][0]["pas"][k]["heure"], du_pas, infos, ecarts)
            touches_h |= touches
            if k % 12 == 11:
                heures.append({"date": date, "heure": J[habitants[0]][0]["pas"][k - 11]["heure"], "faits": len(faits_h), "habitants": sorted(touches_h)})
                faits_h, touches_h = set(), set()
            dernier = (faits, sorted(touches))
    touches_total = sorted(p for p in habitants if par_habitant[p]["faits"])
    cascade = [p for p in touches_total if p not in cibles]
    max_faits = max((h["faits"] for h in heures), default=0)
    if not touches_total:
        ecarts = [p for p, v in details_fin.items() if v[0] >= 0.05 or v[1] >= 0.005 or any(v[2:])]
        verdict = (f"aucune divergence : seuls des détails changent ({', '.join(ecarts)}), que le temps absorbe" if ecarts
                   else "aucune divergence : rien n'a changé dans la vie des habitants")
    elif len(touches_total) >= S["seuil_habitants"] or max_faits >= S["seuil_faits"]:
        verdict = f"paradoxe : {len(touches_total)} habitants touchés, jusqu'à {max_faits} faits différents dans une heure"
    elif dernier[0] == 0:
        fin = next((h for h in reversed(heures) if h["faits"]), None)
        verdict = (f"absorbée : dernier fait différent {quand(fin['date'], fin['heure'])}" if fin else "absorbée")
        if cascade:
            verdict += f", après une cascade jusqu'à {', '.join(cascade)}"
    elif cascade:
        verdict = f"en cascade : la divergence a gagné {', '.join(cascade)} et dure encore à la fin"
    else:
        verdict = f"persistante : {', '.join(touches_total)} reste différent à la fin, sans cascade"
    return {"habitants": habitants, "cibles": list(cibles), "verdict": verdict, "touches": touches_total, "cascade": cascade,
            "premier_fait": premier, "par_habitant": par_habitant, "exemples": exemples, "heures": heures,
            "fin": {"faits": dernier[0], "habitants": dernier[1]},
            "causes": {"interventions": [{k: v for k, v in x.items() if k != "x"} for x in causes.V], "faits": causes.noeuds},
            "arbre": causes.arbre(),
            "details_fin": {p: {"besoins": round(v[0], 2), "emotions": round(v[1], 3), "produits_maison": v[2], "produits_magasin": v[3],
                                "comptes": v[4]} for p, v in details_fin.items()}}


def ecrire_md(r, scenario, journal, chemin):
    L = [f"# Divergence : {scenario.get('description', '')}", ""]
    if scenario.get("attendu"):
        L += [f"**Attendu.** {scenario['attendu']}", ""]
    L += [f"**Verdict : {r['verdict']}.**", ""]
    if r.get("mission"):
        m = r["mission"]
        L += [f"## Mission : {m['titre']} — {m['resultat']}", "", m["raison"], "",
              "Avancement : " + (", ".join(f"{k} : {v}" for k, v in m["avancement"].items()) or "rien") + "."]
        if m["echecs"]:
            L += ["", "Gestes impossibles :", ""] + [f"- {e}" for e in m["echecs"]]
        if m.get("avenir"):
            a = m["avenir"]
            L += ["", f"### L'avenir : {a['titre']}", ""] + [f"- **{x['quand']}** : {x['texte']}" for x in a["frise"]]
            if a.get("nuance"):
                L += ["", a["nuance"]]
        L += [""]
    L += ["## Ce que le voyageur a fait", ""]
    L += [f"- {d} {h} : {t}" for d, h, t in journal] or ["- rien"]
    L += ["", "## Propagation", "", "Premier fait différent pour chaque habitant touché (habitants touchés directement, visés ou témoins : " + (", ".join(r["cibles"]) or "aucun") + ") :", ""]
    for p, x in sorted(r["premier_fait"].items(), key=lambda kv: (kv[1]["date"], kv[1]["heure"])):
        L.append(f"- **{p}**{' (cascade)' if p in r['cascade'] else ''} : {quand(x['date'])} à {x['heure']}, {x['genre']} ({x['detail']})")
    L += ["", "## Chaîne des causes", "", "Chaque fait différent (un épisode, tant qu'il dure) sous ce qui l'a provoqué : l'intervention du voyageur, "
          "le changement chez l'autre pour une rencontre, la dernière rencontre pour ce qu'on apprend, sinon la suite de ce qui a déjà changé pour lui.", ""]
    L += r["arbre"] or ["- aucun fait différent"]
    L += ["", "## Faits par habitant", "", "| Habitant | Pas où un fait diffère | Faits différents | Premier exemple de chaque genre |", "|---|---|---|---|"]
    for p, v in r["par_habitant"].items():
        ex = " ; ".join(f"{g} {d} {h} : {t}" for g, (d, h, t) in r["exemples"].get(p, {}).items())
        L.append(f"| {p} | {v['pas_divergents']} | {v['faits']} | {ex[:400]} |")
    L += ["", "## Heure par heure", "", "Seules les heures où un fait diffère.", "", "| Date | Heure | Faits | Habitants touchés |", "|---|---|---|---|"]
    L += [f"| {h['date']} | {h['heure']} | {h['faits']} | {', '.join(h['habitants'])} |" for h in r["heures"] if h["faits"]]
    L += ["", "## Détails tolérés à la fin de la période", "", "| Habitant | Besoins (écart moyen) | Émotions (écart moyen) | Provisions différentes | Produits du magasin différents | Comptes différents |", "|---|---|---|---|---|---|"]
    for p, v in r["details_fin"].items():
        L.append(f"| {p} | {v['besoins']} | {v['emotions']} | {v['produits_maison']} | {v['produits_magasin']} | {v['comptes']} |")
    open(chemin, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    cibles = args[args.index("--cibles") + 1:] if "--cibles" in args else []
    r = comparer_mondes(args[0], args[1], cibles)
    print(r["verdict"])
    print(json.dumps({k: r[k] for k in ("touches", "cascade", "premier_fait", "par_habitant", "fin")}, ensure_ascii=False, indent=1))
