"""Quartier de Paradoxe : plusieurs habitants vivent en même temps, pas à pas, et se rencontrent.

À chaque pas, chaque habitant décide de ce qu'il fait (habitant.py), puis le
quartier ajoute les rencontres, et chaque pas est enfin calculé par le moteur.

Les règles des rencontres sont générales ; ce qui est propre à chacun est dans
sa fiche, section `relations` (pour chaque personne simulée qu'il connaît :
son nom, l'événement d'un moment passé ensemble, celui d'une absence, et ce
que ce moment apporte au besoin social à chaque pas) :
- deux habitants éveillés au même endroit, sans être occupés à une action
  intime (toilettes, douche), (même lieu, même pièce ou même
  véhicule) sont ensemble : chacun gagne le contact social prévu par sa fiche,
  et le premier pas d'un moment ensemble fait vivre l'événement de la relation ;
- une étape de routine peut être prévue avec quelqu'un (`avec_personnes`) : si
  cette personne n'est venue ni au premier ni au deuxième pas de l'étape,
  l'absence est remarquée et vécue (événement `absence` de la relation).
"""
from habitant import Habitant
from moteur import PAS_PAR_JOUR, hm


class Quartier:
    def __init__(self, fiches, catalogue, date, etats):
        self.fiches = fiches
        self.H = {pid: Habitant(fiches[pid], catalogue, date, etats[pid]) for pid in fiches}
        self.ensemble = set()   # paires (habitant, autre) ensemble au pas précédent
        self.vus = set()        # (habitant, début d'étape, autre) : l'autre est venu pendant l'étape prévue ensemble
        self.absences = set()   # (habitant, début d'étape, autre) : absence déjà remarquée

    def vivre(self):
        while any(h.i < PAS_PAR_JOUR for h in self.H.values()):
            for h in self.H.values():
                h.decider()
            self.rencontres()
            for h in self.H.values():
                h.executer()
        out = {pid: h.terminer() for pid, h in self.H.items()}
        for pid, h in self.H.items():
            h.j.bilan += self.bilan(pid, h)
        return out

    def rencontres(self):
        pos = {}
        for pid, h in self.H.items():
            s = h.attente[1]
            pos[pid] = ((s["lieu"], s["piece"]), s["mode"] != "sommeil" and not h.action_courante.get("intime"))
        ensemble = set()
        for pid, h in self.H.items():
            st = h.attente[0]
            ici, eveille = pos[pid]
            rel = self.fiches[pid].get("relations", {})
            avec = [q for q in self.H if q != pid and eveille and pos[q][1] and pos[q][0] == ici and q in rel]
            for q in avec:
                r = rel[q]
                ensemble.add((pid, q))
                effets = st.setdefault("effets", {})
                if effets.get("social") != "vide":
                    effets["social"] = effets.get("social", 0) + r["social_par_pas"]
                if (pid, q) not in self.ensemble:
                    if r.get("evenement") in h.EV and r["evenement"] not in st.get("ev", []):
                        st.setdefault("ev", []).append(r["evenement"])
                    st["action"] = st["action"].rstrip() + f" Avec {r['nom']}."
            if avec:
                st["ensemble"] = [rel[q]["nom"] for q in avec]
            # moments prévus ensemble : l'autre est-il venu ?
            if h.etape_courante and eveille:
                d, f, e, _ = h.etape_courante
                for q in e.get("avec_personnes", []):
                    if q in avec:
                        self.vus.add((pid, d, q))
                    elif h.i == min(d + 1, f - 1) and (pid, d, q) not in self.vus and (pid, d, q) not in self.absences and q in rel:
                        self.absences.add((pid, d, q))
                        r = rel[q]
                        if r.get("absence") in h.EV:
                            st.setdefault("ev", []).append(r["absence"])
                        st["action"] = st["action"].rstrip() + f" {r['nom']} n'est pas là."
                        h.decisions.append(f"{hm(h.i)} : {r['nom']} n'est pas là pour « {e['action']} ».")
        self.ensemble = ensemble

    def bilan(self, pid, h):
        """Temps passé avec chacun et moments ensemble, d'après les pas de la journée."""
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
        return out
