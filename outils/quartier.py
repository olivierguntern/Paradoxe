"""Quartier de Paradoxe : plusieurs habitants vivent en même temps, pas à pas, et se rencontrent.

À chaque pas, chaque habitant décide de ce qu'il fait (habitant.py), puis le
quartier ajoute les rencontres et les conversations, et chaque pas est enfin
calculé par le moteur. N'importe quel habitant peut y entrer : les règles sont
générales, les valeurs viennent de data/monde/interactions.json (par type de
relation) et de la section `relations` de chaque fiche, qui peut les remplacer.

- Ensemble : deux habitants éveillés dans la même pièce du même logement (ou
  le même lieu public, le même véhicule), sans être occupés à une action
  intime. Chacun gagne le contact social de la relation ; le premier pas
  d'un moment ensemble fait vivre l'événement de rencontre. Une personne
  simulée qu'on ne connaît pas est remarquée comme inconnue.
- Moment prévu ensemble (étape `avec_personnes`) : si la personne n'est venue
  ni au premier ni au deuxième pas, l'absence est remarquée et vécue.
- Conversation : entre deux habitants ensemble et disponibles, selon la
  probabilité de leur relation. Celui qui parle choisit son sujet : une
  préoccupation (à un proche, jamais à la personne qu'elle concerne), ce qu'il
  a fait sans l'autre (pas à un commerçant ni à un client), l'activité
  partagée, une banalité. Ce qu'on a vu d'étrange (un anachronisme du
  voyageur) ou entendu dire se raconte à tout le monde, et se répète. Les textes viennent
  de modèles ; l'interlocuteur retient ce qu'on lui a dit.
- Commerce : quand un habitant achète dans le commerce d'un autre habitant du
  quartier, c'est ce commerçant qui le sert : la vente sort du stock de son
  magasin (dans la limite de ce qui reste en rayon) et la recette va dans sa
  caisse ou sur son compte.
"""
import os
import zlib

from fiches import MONDE, lire
from habitant import Habitant
from moteur import PAS_PAR_JOUR, hm


def tirage(*cle):
    return (zlib.crc32("|".join(map(str, cle)).encode()) % 10000) / 10000


def choix(liste, *cle):
    return liste[zlib.crc32("|".join(map(str, cle)).encode()) % len(liste)]


def minuscule(t):
    """Première lettre en minuscule, sauf sigle (« OL », « SNCF »)."""
    return t if len(t) > 1 and t[1].isupper() else t[:1].lower() + t[1:]


class Quartier:
    def __init__(self, fiches, catalogue, date, etats, voyageur=None):
        self.I = lire(os.path.join(MONDE, "interactions.json"))
        self.fiches = fiches
        self.date = date
        self.V = voyageur       # interventions du voyageur (voyageur.py), ou None : le monde de référence
        self.H = {pid: Habitant(fiches[pid], catalogue, date, etats[pid], voyageur.objets(pid, date) if voyageur else None)
                  for pid in fiches}
        self.ensemble = set()   # paires (habitant, autre) ensemble au pas précédent
        self.vus = set()        # (habitant, début d'étape, autre) : l'autre est venu pendant l'étape prévue ensemble
        self.absences = set()   # (habitant, début d'étape, autre) : absence déjà remarquée
        self.derniere = {}      # paire -> dernier pas de conversation

    # ------------------------------------------------------------ journée
    def vivre(self):
        while any(h.i < PAS_PAR_JOUR for h in self.H.values()):
            for pid, h in self.H.items():
                h.sim.changements_du_monde()   # objets déplacés à son insu, avant qu'il décide
                if not (self.V and self.V.retenir(self, pid, h)):
                    h.decider()
            self.rencontres()
            self.commerces()
            if self.V:
                self.V.agir(self)
            for h in self.H.values():
                h.executer()
        out = {pid: h.terminer() for pid, h in self.H.items()}
        for pid, h in self.H.items():
            h.j.bilan += self.bilan(h)
        return out

    # ------------------------------------------------------------ relations et positions
    def prenom(self, pid):
        return self.fiches[pid]["identite"]["prenom"] if pid in self.fiches else "un passant"

    def relation(self, pid, q):
        """Relation de pid avec q : valeurs du type (interactions.json), remplacées par celles de la fiche."""
        rel = self.fiches[pid].get("relations", {}).get(q)
        T = self.I["types"]
        if rel is None:
            femme = self.fiches[q]["identite"].get("genre") == "femme"
            return dict(T["inconnu"], type="inconnu", nom="une inconnue" if femme else "un inconnu")
        r = dict(T.get(rel.get("type", "connaissance"), T["connaissance"]), type=rel.get("type", "connaissance"), nom=self.prenom(q))
        r.update(rel)
        if "evenement" in rel:  # nom ancien de l'événement de rencontre
            r["rencontre"] = rel["evenement"]
        return r

    def ou(self, pid, h):
        """Où se trouve l'habitant, dans un repère commun à tous : (logement, pièce) ou (lieu, endroit)."""
        s = h.attente[1]
        piece = s["piece"]
        plan = self.fiches[pid]["domicile"]["plan"]
        pc = h.sim.PIECES.get(piece)
        if pc:
            lg = pc.get("logement") or plan.get("logements_des_sites", {}).get(pc.get("lieu")) or f"domicile-{pid}"
            return (lg, pc.get("id_local", piece))
        if piece in h.sim.graph:
            lg = plan.get("logements_des_sites", {}).get(h.site) or f"domicile-{pid}"
            return (lg, piece.split(":")[-1])
        if s["lieu"] == "exterieur" and piece == "trajet":
            return ("trajet", pid)   # chacun sur son propre chemin
        return (s["lieu"], piece)

    # ------------------------------------------------------------ commerces
    def commerces(self):
        """Les achats du pas dans le commerce d'un autre habitant : le commerçant les vend, sur le stock de son magasin."""
        for pid, h in self.H.items():
            A = h.achat
            if not A or A["commerce"] not in self.H or A["commerce"] == pid:
                continue
            o = self.H[A["commerce"]]
            sto = o.attente[0]
            reste = dict(o.sim.boutique)
            for cle in ("ventes", "prelevements"):
                for x in sto.get(cle, []):
                    reste[x["produit"]] = reste.get(x["produit"], 0) - x["quantite"]
            achats, ventes, textes, manque = [], [], [], []
            for x in A["lignes"]:
                cid = x["c"]["produit"]
                n = min(x["n"], max(0, reste.get(cid, 0)))
                reste[cid] = reste.get(cid, 0) - n
                if n < x["n"]:
                    manque.append(x["c"]["nom"].split(" (")[0])
                if n:
                    achats.append({"produit": x["maison"], "quantite": n * x["u"], "prix": round(n * x["c"]["prix"], 2)})
                    ventes.append({"produit": cid, "quantite": n, "paiement": A["paiement"]})
                    textes.append(h.libelle(dict(x, n=n)))
            st = h.attente[0]
            total = round(sum(x["prix"] for x in achats), 2)
            compte = "especes" if A["paiement"] == "especes" else "compte"
            if achats:
                st["achats"], st["argent"] = achats, {compte: -total}
            else:
                st.pop("achats", None)
                st.pop("argent", None)
            if manque:
                st["action"] = st["action"].rstrip() + f" Plus de {', '.join(manque)} en rayon."
                h.decisions.append(f"{hm(h.i)} : plus de {', '.join(manque)} chez {self.prenom(A['commerce'])} ; fait sans.")
            if ventes:
                sto["ventes"] = sto.get("ventes", []) + ventes
                sto["clients"] = sto.get("clients", 0) + 1
                paye = "en espèces" if A["paiement"] == "especes" else "par carte"
                sto["action"] = sto["action"].rstrip() + f" Sert {self.prenom(pid)} : {', '.join(textes)} ({f'{total:.2f}'.replace('.', ',')} €, {paye})."

    # ------------------------------------------------------------ rencontres
    def rencontres(self):
        pos = {}
        for pid, h in self.H.items():
            s = h.attente[1]
            pos[pid] = (self.ou(pid, h), s["mode"] != "sommeil" and not h.action_courante.get("intime"))
        ensemble = set()
        for pid, h in self.H.items():
            st = h.attente[0]
            ici, actif = pos[pid]
            if not actif:
                continue
            avec = [q for q in self.H if q != pid and pos[q][1] and pos[q][0] == ici]
            connus, inconnus = [], []
            for q in avec:
                r = self.relation(pid, q)
                (inconnus if r["type"] == "inconnu" else connus).append(r["nom"])
                ensemble.add((pid, q))
                effets = st.setdefault("effets", {})
                if r["social_par_pas"] and effets.get("social") != "vide":
                    effets["social"] = effets.get("social", 0) + r["social_par_pas"]
                if (pid, q) not in self.ensemble:
                    if r.get("rencontre") in h.EV and r["rencontre"] not in st.get("ev", []):
                        st.setdefault("ev", []).append(r["rencontre"])
                    st["action"] = st["action"].rstrip() + (f" Avec {r['nom']}." if r["type"] != "inconnu" else f" Remarque {r['nom']}.")
            if connus:
                st["ensemble"] = connus
                seul = set(h.action_courante.get("ev_si_seul", []))
                if seul and st.get("ev"):
                    st["ev"] = [e for e in st["ev"] if e not in seul]
            if inconnus:
                st["croise"] = inconnus
            # moments prévus ensemble : l'autre est-il venu ?
            if h.etape_courante:
                d, f, e, _ = h.etape_courante
                for q in e.get("avec_personnes", []):
                    if q in avec:
                        self.vus.add((pid, d, q))
                    elif q in self.H and h.i == min(d + 1, f - 1) and (pid, d, q) not in self.vus | self.absences:
                        self.absences.add((pid, d, q))
                        r = self.relation(pid, q)
                        if r.get("absence") in h.EV:
                            st.setdefault("ev", []).append(r["absence"])
                        st["action"] = st["action"].rstrip() + f" {r['nom']} n'est pas là."
                        h.decisions.append(f"{hm(h.i)} : {r['nom']} n'est pas là pour « {e['action']} ».")
        self.ensemble = ensemble
        self.conversations(pos)

    # ------------------------------------------------------------ conversations
    def conversations(self, pos):
        C = self.I["conversation"]
        ids = sorted(self.H)
        for x, a in enumerate(ids):
            for b in ids[x + 1:]:
                if (a, b) not in self.ensemble:
                    continue
                ha, hb = self.H[a], self.H[b]
                i = ha.i
                if any(h.attente[1]["charge"] in C["sans_attention"] for h in (ha, hb)):
                    continue
                if i - self.derniere.get((a, b), -100) < C["intervalle_pas"]:
                    continue
                ra, rb = self.relation(a, b), self.relation(b, a)
                if tirage(self.date, i, a, b, "conversation") >= max(ra["conversation"], rb["conversation"]):
                    continue
                ea = self.fiches[a]["personnalite"]["big_five"]["extraversion"]
                eb = self.fiches[b]["personnalite"]["big_five"]["extraversion"]
                A, B = (a, b) if tirage(self.date, i, a, b, "qui") < 0.5 + (ea - eb) else (b, a)
                self.derniere[(a, b)] = i
                self.converser(A, B, i, C)

    def sujet(self, A, B, C):
        """Ce dont A parle à B : (genre de sujet, texte, à retenir)."""
        hA, fA = self.H[A], self.fiches[A]
        dit = hA.mem.setdefault("dit", {}).setdefault(B, [])
        if self.relation(A, B)["type"] in C["proches"]:
            prenomB = self.prenom(B)
            for p in sorted(fA["vie_interieure"].get("preoccupations_semaine", []), key=lambda p: -p.get("intensite_initiale", 0)):
                if p.get("intensite_initiale", 0) >= 0.4 and p["id"] not in dit and prenomB not in p["sujet"]:
                    dit.append(p["id"])
                    return "preoccupation", minuscule(p["sujet"]), True
        # ce qu'il a vu d'étrange (ou entendu dire), pas encore raconté à l'autre : on le raconte à tout le monde
        for x in hA.mem.get("anomalies", []):
            cle = "anomalie:" + x["objet"]
            if cle not in dit and x.get("par") != B:
                dit.append(cle)
                return ("anomalie_rapportee" if x.get("par") else "anomalie"), x, False
        # ce qu'il a fait aujourd'hui sans l'autre, le plus long d'abord (pas à un commerçant ni à un client)
        faits = {}
        raconte = self.relation(A, B)["type"] in C.get("racontent_leur_journee", C["proches"])
        for s, a in zip(hA.sim.steps, hA.journal) if raconte else ():
            if a.get("banal") or a.get("intime") or not a or self.prenom(B) in s.get("ensemble", []):
                continue
            faits[s["activite"]] = faits.get(s["activite"], 0) + 1
        for titre, _ in sorted(faits.items(), key=lambda x: -x[1]):
            if "fait:" + titre not in dit and faits[titre] >= 3:
                dit.append("fait:" + titre)
                return "journee", minuscule(titre), True
        sujet = hA.action_courante.get("sujet")
        if sujet and sujet == self.H[B].action_courante.get("sujet"):
            return "activite", sujet, False
        return "banalite", None, False

    def converser(self, A, B, i, C):
        genre, quoi, retenir = self.sujet(A, B, C)
        M = C["modeles"]
        leA = "la" if self.fiches[A]["identite"].get("genre") == "femme" else "le"
        anomalie = quoi if genre.startswith("anomalie") else None
        if anomalie:
            quoi = anomalie["quoi"]
        v = {"A": self.prenom(A), "B": self.prenom(B), "leA": leA, "sujet": quoi, "fait": quoi, "activite": quoi,
             "activite_min": minuscule(quoi or ""), "source": self.prenom(anomalie["par"]) if anomalie and anomalie.get("par") else ""}
        texte = choix(M[genre], self.date, i, A, B, genre).format(**v).replace("?.", " ?").replace("!.", " !").replace("  ", " ")
        if anomalie:
            texte += " " + M["reponse_etonnee"].format(**v)
            hB = self.H[B]
            if anomalie["objet"] not in {x["objet"] for x in hB.mem.get("anomalies", [])}:
                hB.mem.setdefault("anomalies", []).append({"date": self.date, "heure": hm(i), "objet": anomalie["objet"], "quoi": quoi, "par": A})
        if genre in ("preoccupation", "journee"):
            agreable = self.fiches[B]["personnalite"]["big_five"]["agreabilite"] >= 0.6
            texte += " " + (M["reponse_chaleureuse"] if agreable and genre == "preoccupation" else M["reponse_breve"]).format(**v)
        E = C["evenements"]
        for qui, role, ev in ((A, "parle", E["confie"] if genre == "preoccupation" else None), (B, "ecoute", E["ecoute"] if genre == "preoccupation" else None)):
            h = self.H[qui]
            st = h.attente[0]
            st["action"] = st["action"].rstrip() + " " + texte
            st["conversation"] = {"avec": self.prenom(B if qui == A else A), "role": role, "sujet": genre, "texte": texte}
            for e in (E["tous"], ev):
                if e and e in h.EV and e not in st.get("ev", []):
                    st.setdefault("ev", []).append(e)
        if retenir:
            self.H[B].mem.setdefault("appris", []).append({"date": self.date, "heure": hm(i), "de": A, "sujet": genre, "quoi": quoi})

    # ------------------------------------------------------------ bilan
    def bilan(self, h):
        """Temps passé avec chacun, moments ensemble, conversations et ce qu'il a appris dans la journée."""
        out, par = [], {}
        for s in h.sim.steps:
            for nom in s.get("ensemble", []):
                par.setdefault(nom, []).append(s)
        for nom, pas in par.items():
            moments, debut, prec = [], None, None
            for s in pas:
                if prec is None or s["pas"] != prec["pas"] + 1:
                    if debut:
                        moments.append(f"{debut['heure']}–{hm(prec['pas'] + 1)} {debut['activite']}")
                    debut = s
                prec = s
            moments.append(f"{debut['heure']}–{hm(prec['pas'] + 1)} {debut['activite']}")
            out.append(f"**Avec {nom} : {len(pas) * 5 // 60} h {len(pas) * 5 % 60:02d}** — " + " ; ".join(moments))
        conv = [f"{s['heure']} {s['conversation']['texte']}" for s in h.sim.steps if s.get("conversation")]
        if conv:
            out.append(f"**Conversations ({len(conv)})** : " + " / ".join(conv))
        appris = [f"{x['heure']} de {self.prenom(x['de'])} : {x['quoi']}" for x in h.mem.get("appris", []) if x["date"] == self.date]
        if appris:
            out.append("**Appris** : " + " / ".join(appris))
        croises = sorted({n for s in h.sim.steps for n in s.get("croise", [])})
        if croises:
            out.append("**Inconnus remarqués** : " + ", ".join(croises))
        return out
