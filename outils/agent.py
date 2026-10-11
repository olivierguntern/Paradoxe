"""Agent autonome de Paradoxe.

L'agent décide lui-même, pas après pas, de ce que fait le personnage. Il suit
le plan de sa journée (data/agents/<personnage>/regles.json), ses recettes
(blocs, repas, travaux, séances) et l'adapte à son état, lu à chaque pas dans
la simulation : besoins, émotions, objets, provisions, avancement des travaux.

Principales règles de décision :
- réveil par la sonnerie, ou naturel après un sommeil long ;
- travaux pris par ordre de priorité, avec cycles de machine, observations de
  24 h, validations prioritaires et tâches légères dans la dernière heure ;
- plat long à cuire mis en route avant midi ; dîner terminé à 20:00 ;
- séance du soir écourtée si l'énergie passe sous le seuil de fatigue ;
- durée d'endormissement selon l'anxiété et l'excitation ;
- habitude apprise après un oubli (ranger le livre) ;
- pensées et rêves choisis dans des modèles, de façon déterministe.
"""
import copy
import datetime
import json
import os
import zlib

from moteur import PAS_PAR_JOUR, Incoherence, Journee, Simulation, hm, idx

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
NEZ = "sur son nez"
ETUI = "atelier / établi, dans leur étui"


def choix(liste, *cle):
    """Choix déterministe dans une liste."""
    return liste[zlib.crc32("|".join(map(str, cle)).encode()) % len(liste)]


def tirage(*cle):
    """Nombre déterministe entre 0 et 1."""
    return (zlib.crc32("|".join(map(str, cle)).encode()) % 1000) / 1000


def phase_sommeil(minutes):
    """Phase de sommeil selon les minutes écoulées depuis l'endormissement (cycles de 90 minutes)."""
    k, o = divmod(minutes, 90)
    motifs = [
        [(15, "léger"), (60, "profond"), (75, "léger"), (90, "paradoxal")],
        [(10, "léger"), (55, "profond"), (70, "léger"), (90, "paradoxal")],
        [(10, "léger"), (40, "profond"), (60, "léger"), (90, "paradoxal")],
        [(5, "micro-éveil"), (20, "léger"), (35, "profond"), (60, "léger"), (90, "paradoxal")],
        [(20, "léger"), (30, "profond"), (55, "léger"), (85, "paradoxal"), (90, "léger")],
        [(30, "léger"), (50, "paradoxal"), (90, "léger")],
    ]
    for fin, phase in motifs[min(k, 5)]:
        if o < fin:
            return phase
    return "léger"


class Agent:
    def __init__(self, fiche, dossier, date, etat):
        self.fiche = fiche
        self.R = json.load(open(os.path.join(dossier, "regles.json")))
        self.BLOCS = json.load(open(os.path.join(dossier, "blocs.json")))
        self.TRAVAUX = json.load(open(os.path.join(dossier, "travaux.json")))
        self.SEANCES = json.load(open(os.path.join(dossier, "seances.json")))
        self.REPAS = json.load(open(os.path.join(dossier, "repas.json")))
        self.PENSEES = json.load(open(os.path.join(dossier, "pensees.json")))
        self.date = date
        d = datetime.date.fromisoformat(date)
        self.jour = JOURS[d.weekday()]
        self.date_txt = f"{d.day} {MOIS[d.month - 1]}"
        self.etat_initial = copy.deepcopy(etat)
        self.sim = Simulation(fiche, date, etat)
        self.mem = copy.deepcopy(etat.get("agent")) or self.memoire_initiale()
        self.mem["jour_index"] = self.mem.get("jour_index", -1) + 1
        self.mem["evocations_du_jour"] = {}
        self.j = Journee(date, self.jour, extinction="23:00")
        self.j.methode = [
            "Généré par l'agent autonome (outils/agent.py) à partir de ses recettes et règles (data/agents/).",
            "Calculé par outils/moteur.py avec les règles de la fiche : déplacements, lumière, besoins, émotions et concentration.",
            "Pensées et rêves choisis dans des modèles de façon déterministe.",
            "La journée part de l'état exact de la fin de la veille.",
        ]
        self.faits = []      # pour le carnet
        self.decisions = []  # écarts et décisions notables
        self.moments = {(m["bloc"], m["pas"]) for m in self.PENSEES["moments"]}

    # ------------------------------------------------------------ mémoire
    def memoire_initiale(self):
        veille = idx(self.R["endormi_la_veille_du_premier_jour"]) - PAS_PAR_JOUR
        return {
            "endormi_a": veille, "habitudes": {"ranger_livre": False},
            "poubelle": {"id": "obj-poubelle", "repas": self.R["poubelle"]["repas_au_depart"], "numero": 1},
            "page": self.R["lecture"]["page_au_depart"],
            "travaux": {t["id"]: {"phase": 0, "op": 0, "dispo": None, "machine_fin": None, "termine": False} for t in self.TRAVAUX["liste"]},
            "courant": None, "intercale": None, "entretien": 0,
            "seance": {"numero": 1, "op": 0}, "evocations": {},
        }

    @property
    def i(self):
        return len(self.sim.steps)

    def abs(self, i=None):
        return self.mem["jour_index"] * PAS_PAR_JOUR + (self.i if i is None else i)

    # ------------------------------------------------------------ émission d'un pas
    def emettre(self, pas, titre, routine, bloc=None, k=None, pensee=None):
        st = copy.deepcopy(pas)
        s = {"titre": titre, "routine": routine, "piece": st.pop("piece", self.sim.piece), "lieu": st.pop("lieu", "domicile"),
             "mode": st.pop("mode", "eveille"), "charge": st.pop("charge", "simple"), "posture": st.pop("posture", "debout")}
        for cle in ("leger", "machine", "pendant_machine", "moment"):
            st.pop(cle, None)
        # cohérence des lunettes : un geste déjà fait n'est pas refait
        if "objets" in st:
            st["objets"] = [o for o in st["objets"] if not (o["objet"] == "obj-lunettes" and self.sim.positions["obj-lunettes"] != o["de"])]
        if "{travail}" in st["action"]:
            prochain = next((t["titre"] for t in self.TRAVAUX["liste"] if not self.mem["travaux"][t["id"]]["termine"]
                             and self.op_suivante(t) is not None), "montre en cours")
            st["action"] = st["action"].replace("{travail}", prochain)
        L = self.R["lecture"]
        deja_fini = self.mem.get("livre_termine", False)
        if s["mode"] == "lecture" and not deja_fini:
            self.mem["page"] = min(L["pages_total"], self.mem["page"] + L["pages_par_pas"])
            if self.mem["page"] >= L["pages_total"]:
                self.mem["livre_termine"] = True
                st.setdefault("ev", []).append("livre_termine")
                st["pensee"] = st.get("pensee") or choix(self.PENSEES["evenements"]["livre_termine"], self.date, self.i)
                self.faits.append(self.PENSEES["livre_termine"])
                self.decisions.append(f"{hm(self.i)} : termine « La Route ».")
        if "{page}" in st["action"]:
            if deja_fini:
                st["action"] = st["action"].replace("(page {page})", "(relit les dernières pages)")
            st["action"] = st["action"].replace("{page}", str(self.mem["page"]))
        # très assoiffé, il boit un deuxième verre
        eau = st.get("effets", {}).get("soif")
        if isinstance(eau, (int, float)) and eau >= 20 and s["mode"] != "sommeil" and self.sim.besoins["soif"] - 0.7 + eau < 45:
            st["effets"] = dict(st["effets"], soif=eau + 20)
            st["action"] = st["action"].rstrip() + " Boit un deuxième verre d'eau."
            self.decisions.append(f"{hm(self.i)} : très assoiffé ({round(self.sim.besoins['soif'], 1)}) ; boit un deuxième verre.")
        st.setdefault("pensee", None)
        if pensee is not None:
            st["pensee"] = pensee
        if not st["pensee"]:
            moment = (bloc, k) in self.moments or pas.get("moment")
            if moment:
                self.preoccupation(st)
            else:
                for ev in st.get("ev", []):
                    modeles = self.PENSEES["evenements"].get(ev)
                    if modeles and tirage(self.date, self.i, ev) < self.PENSEES["frequence_evenements"]:
                        st["pensee"] = choix(modeles, self.date, self.i, ev)
                        break
        if st.get("mode") == "sommeil" or s["mode"] == "sommeil":
            pass
        entree = self.sim.pas(st, s)
        segs = self.j.segments
        if segs and segs[-1]["titre"] == titre and segs[-1].get("_bloc") == (bloc or titre):
            segs[-1]["pas"].append(st)
        else:
            segs.append({"debut": hm(entree["pas"]), "titre": titre, "routine": routine, "pas": [st], "_bloc": bloc or titre})
        return entree

    def preoccupation(self, st):
        """Choisit la préoccupation la plus pesante et l'ajoute comme pensée."""
        prs = {p["id"]: p for p in self.fiche["vie_interieure"]["preoccupations_semaine"]}
        meilleur, score = None, -1
        for pid, spec in self.PENSEES["preoccupations"].items():
            if pid not in prs:
                continue
            if spec.get("max_par_jour") and self.mem["evocations_du_jour"].get(pid, 0) >= spec["max_par_jour"]:
                continue
            if spec.get("si_social_sous") and self.sim.besoins["social"] >= spec["si_social_sous"]:
                continue
            depuis = self.abs() - self.mem["evocations"].get(pid, -10 ** 6)
            sc = prs[pid]["intensite_initiale"] * (1 + min(depuis, 2000) / 60)
            if sc > score:
                meilleur, score = pid, sc
        if not meilleur:
            return
        spec = self.PENSEES["preoccupations"][meilleur]
        st["pensee"] = choix(spec["textes"], self.date, self.i, meilleur)
        if spec["evenement"]:
            st.setdefault("ev", []).append(spec["evenement"])
        self.mem["evocations"][meilleur] = self.abs()
        self.mem["evocations_du_jour"][meilleur] = self.mem["evocations_du_jour"].get(meilleur, 0) + 1

    # ------------------------------------------------------------ interruptions par les besoins
    def prochain_repas(self):
        if self.jour == "dimanche" and self.i < idx("11:00"):
            return idx("11:00")
        if self.i < idx("12:30"):
            return idx("12:30")
        if self.i < idx("19:00"):
            return idx("19:00")
        return None

    def interruption(self, fin=None):
        """Si un besoin passe sous son seuil d'alerte, l'agent s'interrompt pour y répondre (un pas), puis reprend."""
        if fin is not None and fin - self.i <= 2:
            return False
        B, seuil = self.sim.besoins, {n: self.fiche["besoins"][n]["seuil_alerte"] for n in ("toilettes", "soif", "faim")}
        p = None
        if B["toilettes"] < seuil["toilettes"]:
            p = {"action": "S'interrompt pour passer aux toilettes.", "piece": "wc", "effets": {"toilettes": "vide"}}
            quoi = "toilettes"
        elif B["soif"] < seuil["soif"]:
            p = {"action": "S'interrompt pour boire un grand verre d'eau à la cuisine.", "piece": "cuisine", "effets": {"soif": 25},
                 "pensee": "Soif."}
            quoi = "soif"
        elif B["faim"] < seuil["faim"]:
            repas = self.prochain_repas()
            if repas is None or repas - self.i > 9:
                for pid, txt, q in (("pommes", "une pomme", 1), ("oranges", "une orange", 1), ("bananes", "une banane", 1),
                                    ("biscottes", "deux biscottes", 2)):
                    if self.sim.stock.get(pid, 0) >= q:
                        p = {"action": f"S'interrompt pour manger {txt} à la cuisine.", "piece": "cuisine", "effets": {"faim": 15},
                             "consommation": [{"produit": pid, "quantite": q}], "pensee": "Un petit creux."}
                        quoi = "faim"
                        break
        if not p:
            return False
        p.update({"charge": "simple", "posture": "debout"})
        self.decisions.append(f"{hm(self.i)} : {quoi} sous le seuil d'alerte ({round(B[quoi], 1)}) ; s'interrompt.")
        self.emettre(p, "Besoin pressant", "interruption", bloc="interruption")
        return True

    def bloc(self, bid, titre=None, remplace=None, limite=None):
        b = self.BLOCS[bid]
        for k, pas in enumerate(b["pas"][:limite]):
            pas = copy.deepcopy(pas)
            if remplace:
                remplace(k, pas)
            self.emettre(pas, titre or b["titre"], b["routine"], bloc=bid, k=k)

    # ------------------------------------------------------------ lunettes et lampe
    def mettre_lunettes(self, pas, texte=True):
        if self.sim.positions["obj-lunettes"] == ETUI:
            pas.setdefault("objets", []).insert(0, {"objet": "obj-lunettes", "de": ETUI, "vers": NEZ})
            if texte:
                if "lampe-etabli" not in self.sim.appareils:
                    pas.setdefault("app", {}).setdefault("allume", []).append("lampe-etabli")
                    pas["action"] = "Rallume la lampe, remet ses lunettes. " + pas["action"]
                else:
                    pas["action"] = "Remet ses lunettes. " + pas["action"]

    def poser_lunettes(self, pas):
        if self.sim.positions["obj-lunettes"] == NEZ:
            pas.setdefault("objets", []).insert(0, {"objet": "obj-lunettes", "de": NEZ, "vers": ETUI})

    # ------------------------------------------------------------ nuit et réveil
    def nuit(self):
        onset = self.mem["endormi_a"]
        sonnerie = idx(self.R["heure_sonnerie"]) if self.jour in self.R["jours_sonnerie"] else None
        hier = JOURS[(JOURS.index(self.jour) - 1) % 7]
        titre = f"Nuit de {hier} à {self.jour}"
        reve, n_rem, ancien = None, 0, None
        while True:
            i = self.i
            m = (i - onset) * 5
            phase = phase_sommeil(m)
            if sonnerie is not None and i >= sonnerie:
                return "sonnerie"
            if sonnerie is not None and m >= self.R["reveil_naturel"]["sommeil_minimum_minutes"] and phase == "léger" \
                    and i >= idx(self.R["reveil_naturel"]["pas_avant"]):
                return "naturel"
            if sonnerie is None:
                W = self.R["reveil_week_end"]
                if i >= idx(W["heure_max"]) or (m >= self.R["reveil_naturel"]["sommeil_minimum_minutes"] and phase == "léger" and i >= idx(W["pas_avant"])):
                    return "naturel"
            ev = []
            if phase == "paradoxal" and ancien != "paradoxal":
                theme = self.PENSEES["ordre_des_reves"][(n_rem + self.mem["jour_index"]) % len(self.PENSEES["ordre_des_reves"])]
                reve = choix(self.PENSEES["reves"][theme], self.date, i, theme)
                e = self.PENSEES["evenements_des_reves"].get(theme)
                if e:
                    ev = [e]
                n_rem += 1
            if phase != "paradoxal":
                reve = None
            action = "Se retourne, remonte la couette et se rendort." if phase == "micro-éveil" else "Dort."
            pas = {"action": action, "piece": "chambre", "mode": "sommeil", "charge": "sommeil", "posture": "allongé",
                   "phase_sommeil": phase}
            if reve:
                pas["reve"] = reve
            if ev:
                pas["ev"] = ev
            self.emettre(pas, titre, "sommeil", bloc="nuit")
            ancien = phase

    # ------------------------------------------------------------ matin
    def matin(self, reveil):
        course = self.jour in self.R["jours_course"]
        if reveil == "naturel":
            sonnerie = idx(self.R["heure_sonnerie"])
            self.bloc("eveil_naturel")
            while self.i < sonnerie:
                self.emettre({"action": "Reste allongé, les yeux ouverts.", "piece": "chambre", "charge": "repos", "posture": "allongé"},
                             "Éveil avant la sonnerie", "rt-matin-simple", bloc="eveil_naturel")
            self.decisions.append(f"{hm(self.i - 1)} : réveil naturel avant la sonnerie (sommeil long).")
        for etape in self.R["matin_course" if course else "matin_simple"]:
            if etape in ("reveil", "reveil_course"):
                if reveil == "naturel":
                    self.bloc("lever_avant_sonnerie")
                else:
                    def lampe(k, pas):
                        if self.i >= self.sim.LEVER and "app" in pas:
                            pas["app"]["allume"] = [a for a in pas["app"].get("allume", []) if a != "lumiere-chambre"]
                    self.bloc("reveil_sonnerie_course" if course else "reveil_sonnerie", remplace=lampe)
            elif etape == "douche":
                self.bloc("douche_rasage" if self.jour in self.R["jours_rasage_sans_course"] else "douche")
            elif etape == "lecture_technique":
                self.lecture_technique()
            elif etape == "depart_course":
                self.depart_course()
            elif etape == "descente_saone":
                pb = self.mem["poubelle"]
                def sac(k, pas):
                    if k == 0:
                        if pb.get("en_main"):
                            pas["objets"] = [{"objet": pb["en_main"], "de": "dans sa main", "vers": "local poubelles de l'immeuble"}]
                        else:
                            pas.pop("objets", None)
                            pas["action"] = pas["action"].replace(", dépose le sac au local poubelles", "")
                self.bloc("descente_saone", remplace=sac)
                pb.pop("en_main", None)
            elif etape == "toilettes_eau":
                def boire(k, pas):
                    if self.sim.besoins["soif"] - 0.7 + 20 < 60:
                        pas["effets"]["soif"] = 40
                        pas["action"] = "Passe aux toilettes, puis boit deux grands verres d'eau au lavabo."
                        pas["pensee"] = "Soif. Deux verres, avant de courir."
                        self.decisions.append(f"{hm(self.i)} : soif au réveil ({round(self.sim.besoins['soif'], 1)}) ; boit deux verres avant de courir.")
                self.bloc("toilettes_eau", remplace=boire)
            elif etape == "tenue_course":
                self.tenue_course()
            elif etape in ("ouverture_atelier", "ouverture_atelier_reglage"):
                self.ouverture_atelier(etape)
            else:
                self.bloc(etape)
        if course:
            self.faits.append("7 km")

    def tenue_course(self):
        ou = self.sim.positions["obj-tenue-course"]
        def tenue(k, pas):
            if ou != pas["objets"][0]["de"]:
                support = ou.split(" / ", 1)[1]
                pas["objets"][0]["de"] = ou
                if support == "étendoir":
                    pas["action"] = "Prend sa tenue de course sur l'étendoir, sèche juste à temps, et l'enfile avec son bonnet."
                elif support == "panier à linge":
                    pas["action"] = "Reprend sa tenue de course dans le panier à linge : elle a déjà servi, elle fera l'affaire."
                    pas["pensee"] = "Mercredi prochain, la machine."
                else:
                    pas["action"] = f"Prend sa tenue de course ({support}) et l'enfile."
                self.decisions.append(f"{hm(self.i)} : la tenue de course n'est pas dans l'armoire ({ou}) ; il la prend où elle est.")
        self.bloc("tenue_course", remplace=tenue)

    def depart_course(self):
        pb = self.mem["poubelle"]
        if pb["repas"] >= self.R["poubelle"]["repas_avant_descente"]:
            nouveau = f"obj-poubelle-{pb['numero'] + 1}"
            ancien = pb["id"]
            def sac(k, pas):
                pas["objets"] = [o if o["objet"] != "obj-poubelle" else dict(o, objet=ancien) for o in pas["objets"]]
                pas["nouveaux_objets"] = [{"id": nouveau, "nom": "Sac-poubelle de la cuisine (neuf)", "position": "cuisine / poubelle sous l'évier"}]
            self.bloc("depart_course", remplace=sac)
            pb.update({"id": nouveau, "numero": pb["numero"] + 1, "repas": 0, "en_main": ancien})
            self.decisions.append(f"{hm(self.i - 1)} : descend la poubelle en partant courir ({self.R['poubelle']['repas_avant_descente']} repas ou plus depuis la dernière fois).")
        else:
            self.bloc("depart_course_sans_poubelle")

    def lecture_technique(self):
        fin = idx(self.R["fin_lecture_technique"])
        seance = self.seance_du_soir()
        bid = "lecture_technique_manuel" if seance and seance.get("preparer_lecture") else "lecture_technique_ordinateur"
        pas = self.BLOCS[bid]["pas"]
        k = 0
        while self.i < fin:
            if self.interruption(fin):
                continue
            self.emettre(copy.deepcopy(pas[min(k, len(pas) - 1)]), self.BLOCS[bid]["titre"], self.BLOCS[bid]["routine"], bloc=bid, k=k)
            k += 1

    def ouverture_atelier(self, bid):
        txt = []
        for t in self.TRAVAUX["liste"]:
            m = self.mem["travaux"][t["id"]]
            ph = t["phases"][m["phase"]] if m["phase"] < len(t["phases"]) else None
            if t.get("ouverture_si_observation") and ph and ph.get("validation") and m["dispo"] and m["dispo"] > self.abs():
                txt.append(t["ouverture_si_observation"])
        def ajout(k, pas):
            if txt:
                pas["action"] += " " + " ".join(txt)
        self.bloc(bid, remplace=ajout)

    # ------------------------------------------------------------ travaux
    def phase(self, t):
        m = self.mem["travaux"][t["id"]]
        return t["phases"][m["phase"]] if m["phase"] < len(t["phases"]) else None

    def op_suivante(self, t):
        if t.get("jours") and self.jour not in t["jours"]:
            return None
        ph = self.phase(t)
        if not ph or "ops" not in ph:
            return None
        m = self.mem["travaux"][t["id"]]
        if m["dispo"] is not None and m["dispo"] > self.abs():
            return None
        return ph["ops"][m["op"]]

    def avancer(self, t):
        m = self.mem["travaux"][t["id"]]
        m["op"] += 1
        ph = self.phase(t)
        if m["op"] >= len(ph["ops"]):
            m["phase"] += 1
            m["op"] = 0
            m["dispo"] = None
            suiv = self.phase(t)
            if suiv is None:
                m["termine"] = True
                return "fin"
            if "attente" in suiv:
                if suiv["attente"] == "observation":
                    m["dispo"] = self.abs() - 1 + PAS_PAR_JOUR
                elif suiv["attente"] == "pas":
                    m["dispo"] = self.abs() - 1 + suiv["pas"]
                else:
                    m["dispo"] = (self.mem["jour_index"] + 1) * PAS_PAR_JOUR + idx(self.R["atelier"][0]["debut"])
                m["phase"] += 1
                if suiv["attente"] == "observation":
                    self.faits.append(f"{t['titre']} terminée, en observation")
                return "attente"
            return "phase"
        return None

    def choisir_operation(self):
        T = {t["id"]: t for t in self.TRAVAUX["liste"]}
        ordre = [t["id"] for t in self.TRAVAUX["liste"]]
        # 1. une validation disponible passe avant tout
        for tid in ordre:
            ph = self.phase(T[tid])
            if ph and ph.get("validation") and self.op_suivante(T[tid]) is not None:
                return tid
        # 2. un groupe intercalé se termine
        if self.mem["intercale"]:
            return self.mem["intercale"]
        # 3. le travail en cours continue, en tenant compte d'un cycle de machine
        cour = self.mem["courant"]
        if cour and self.op_suivante(T[cour]) is not None:
            m = self.mem["travaux"][cour]
            op = self.op_suivante(T[cour])
            if m["machine_fin"] and self.abs() < m["machine_fin"] and not op.get("pendant_machine"):
                for tid in ordre:
                    ph = self.phase(T[tid])
                    if tid != cour and ph and ph.get("intercalable") and self.op_suivante(T[tid]) is not None:
                        self.mem["intercale"] = tid
                        return tid
                return "attente_machine"
            return cour
        # 4. un nouveau travail, par ordre de priorité (seulement du léger dans la dernière heure)
        derniere_heure = self.i >= idx(self.TRAVAUX["derniere_heure"])
        for tid in ordre:
            op = self.op_suivante(T[tid])
            if op is not None and (not derniere_heure or op.get("leger")):
                self.mem["courant"] = tid
                return tid
        return None

    def atelier(self, debut, fin, fin_de_seance=False, avance=None):
        fin = idx(fin)
        T = {t["id"]: t for t in self.TRAVAUX["liste"]}
        premier = True
        while self.i < fin:
            if avance and self.i == avance[0]:
                pas_av = avance[1]
                for k, p in enumerate(pas_av):
                    p = copy.deepcopy(p)
                    if k == 0:
                        self.poser_lunettes(p)
                        if p.get("objets") and p["objets"][0]["objet"] == "obj-lunettes":
                            p["action"] = "Pose ses lunettes. " + p["action"]
                    self.emettre(p, "Préparation du déjeuner", "préparation anticipée", bloc="avance_repas")
                self.decisions.append(f"{hm(avance[0])} : met le déjeuner en route avant midi (cuisson longue).")
                premier = True
                continue
            if fin_de_seance and self.i == fin - 1:
                p = {"action": "Éteint la lampe, pose ses lunettes.", "piece": "atelier", "mode": "travail", "charge": "precision",
                     "posture": "assis", "app": {"eteint": ["lampe-etabli"]},
                     "pensee": choix(self.PENSEES["fin_de_seance_travail"], self.date, self.i)}
                self.poser_lunettes(p)
                self.emettre(p, self.titre_atelier(), "rt-atelier", bloc="atelier")
                break
            if self.interruption(fin):
                continue
            tid = self.choisir_operation()
            if tid in (None, "attente_machine"):
                k = self.mem["entretien"]
                op = copy.deepcopy(self.TRAVAUX["entretien"][k % len(self.TRAVAUX["entretien"])]) if tid is None else \
                    {"action": "Surveille la machine en rangeant l'établi.", "charge": "simple", "posture": "assis"}
                self.mem["entretien"] += 1
                titre = "Entretien de l'atelier"
            else:
                op = copy.deepcopy(self.op_suivante(T[tid]))
                titre = self.titre_atelier(T[tid])
            op.setdefault("piece", "atelier")
            op.setdefault("mode", "travail")
            if premier:
                self.mettre_lunettes(op)
                if self.i == idx(self.R["atelier"][0]["debut"]) and op["action"].startswith("Remet ses lunettes. "):
                    op["action"] = op["action"].replace("Remet ses lunettes. ", "Chausse ses lunettes. ", 1)
                premier = False
            # fin automatique d'un cycle de machine
            for t in self.TRAVAUX["liste"]:
                m = self.mem["travaux"][t["id"]]
                if m["machine_fin"] and self.abs() == m["machine_fin"]:
                    op.setdefault("app", {}).setdefault("eteint", [])
                    if "machine-ultrasons" not in op["app"]["eteint"]:
                        op["app"]["eteint"].append("machine-ultrasons")
                    m["machine_fin"] = None
            if tid not in (None, "attente_machine"):
                t = T[tid]
                pos = self.sim.positions.get(t["objet"], "")
                ph = self.phase(t)
                if t.get("a_sortir") and not pos.startswith("atelier / établi") and not (ph and ph.get("validation")) \
                        and not any(o["objet"] == t["objet"] and o["de"] == pos for o in op.get("objets", [])):
                    op.setdefault("objets", []).append({"objet": t["objet"], "de": pos, "vers": "atelier / établi"})
                    op["action"] = f"Sort {t['designation']} du coffre. " + op["action"]
                brut = self.op_suivante(T[tid])
                if brut.get("machine"):
                    self.mem["travaux"][tid]["machine_fin"] = self.abs() + brut["machine"]
                self.emettre(op, titre, "rt-atelier", bloc="atelier_" + tid)
                etat = self.avancer(T[tid])
                if etat and self.mem["intercale"] == tid:
                    self.mem["intercale"] = None
                if etat in ("fin", "attente") and self.mem["courant"] == tid:
                    self.mem["courant"] = None
                if etat == "fin" and self.phase(T[tid]) is None and T[tid]["phases"][-1].get("validation"):
                    self.faits.append(f"{T[tid]['titre']} validée")
                if etat == "fin" and T[tid]["id"] == "quartz":
                    self.faits.append("Montres à quartz prêtes")
            else:
                self.emettre(op, titre, "rt-atelier", bloc="atelier_entretien")

    def titre_atelier(self, t=None):
        if t is None:
            return "Fin de séance à l'atelier"
        ph = self.phase(t)
        return f"{t['titre']} : {ph.get('titre', 'travail')}" if ph and ph.get("titre") else t["titre"]

    def rangement_atelier(self):
        objets = []
        for t in self.TRAVAUX["liste"]:
            pos = self.sim.positions.get(t["objet"], "")
            if pos.startswith("atelier / établi"):
                m = self.mem["travaux"][t["id"]]
                ph = self.phase(t)
                cle = "observation" if (ph and ph.get("validation") and m["dispo"]) else "en_cours"
                vers = t["rangement"].get(cle, t["rangement"]["en_cours"])
                objets.append({"objet": t["objet"], "de": pos, "vers": vers})
        objets.append({"objet": "obj-cles-coffre", "de": "atelier / serrure du coffre", "vers": "atelier / tiroir de l'établi, à droite"})
        self.emettre({"action": "Range les montres en cours au coffre, ferme et remet la clé dans le tiroir.", "piece": "atelier",
                      "mode": "travail", "charge": "simple", "posture": "debout", "objets": objets}, "Rangement de l'atelier", "rt-atelier")
        p = {"action": "Aligne ses outils, éteint la lampe, range ses lunettes.", "piece": "atelier", "mode": "travail", "charge": "simple",
             "posture": "debout", "app": {"eteint": ["lampe-etabli"]}, "ev": ["repos_merite"]}
        self.poser_lunettes(p)
        self.emettre(p, "Rangement de l'atelier", "rt-atelier")

    # ------------------------------------------------------------ repas
    def avance_dejeuner(self):
        r = self.REPAS["midi"].get(self.jour, {})
        if r.get("avance_minutes"):
            return (idx("12:30") - r["avance_minutes"] // 5, r["avance"])
        return None

    def dejeuner(self):
        r = self.REPAS["midi"][self.jour]
        for k, p in enumerate(r["repas"]):
            self.emettre(copy.deepcopy(p), "Déjeuner", "rt-atelier", bloc="dejeuner", k=k)
        self.mem["poubelle"]["repas"] += 1
        if r.get("apres"):
            for k, p in enumerate(r["apres"]):
                self.emettre(copy.deepcopy(p), "Café et vaisselle", "rt-atelier", bloc="apres_dejeuner", k=k)
        else:
            self.bloc("cafe_vaisselle")

    def repos(self):
        self.bloc("repos_chambre")
        if self.mem["habitudes"]["ranger_livre"]:
            self.bloc("lecture_courte")
            self.bloc("rangement_livre")
        else:
            self.bloc("lecture_sieste")

    def pause_fruit(self):
        self.bloc(self.R["fruits_de_l_apres_midi"][self.mem["jour_index"] % len(self.R["fruits_de_l_apres_midi"])])

    def diner(self):
        r = self.REPAS["soir"][self.jour]
        parties = [("preparation", "Préparation du dîner"), ("attente", "Lecture pendant la cuisson"), ("finition", "Fin de la cuisson"),
                   ("repas", "Dîner"), ("apres", "Vaisselle")]
        for cle, titre in parties:
            for k, p in enumerate(r.get(cle) or []):
                self.emettre(copy.deepcopy(p), titre, "rt-soir", bloc="diner_" + cle, k=k)
        self.mem["poubelle"]["repas"] += 1

    def longueur_diner(self):
        r = self.REPAS["soir"][self.jour]
        return sum(len(r.get(c) or []) for c in ("preparation", "attente", "finition", "repas", "apres"))

    # ------------------------------------------------------------ soirée
    def temps_libre(self, jusqua):
        T = self.BLOCS["temps_libre"]["pas"]
        n = jusqua - self.i
        if n <= 0:
            return
        if n <= 4:
            suite = [(T[k], k) for k in range(n)]
        else:
            ecoute = [T[5 + (k % 6)] for k in range(n - 6)]
            suite = [(T[k], k) for k in range(4)] + [(T[4], 4)] + [(p, 5) for p in ecoute] + [(T[11], 11)]
        for p, k in suite:
            if self.interruption(jusqua):
                if self.i >= jusqua:
                    break
            p = copy.deepcopy(p)
            p["action"] = p["action"].replace("La nuit tombe : il se lève allumer le séjour, puis se rallonge.", "Le disque continue.")
            self.emettre(p, "Temps libre", "rt-soir", bloc="temps_libre", k=k)

    def seance_du_soir(self):
        n = self.mem["seance"]["numero"]
        for s in self.SEANCES["liste"]:
            if s["numero"] == n:
                return s
        return None

    def seance(self, fin_ops):
        s = self.seance_du_soir()
        fin_ops = idx(fin_ops)
        p = copy.deepcopy(self.BLOCS["ouverture_seance"]["pas"][0])
        if "radio" in self.sim.appareils:
            p.setdefault("app", {}).setdefault("eteint", []).append("radio")
            p["via"] = ["sejour"]
        self.mettre_lunettes(p, texte=False)
        if s is None:
            self.emettre(p, "Montre du grand-père", "rt-soir", bloc="seance")
            return
        titre = s["titre"]
        self.emettre(p, titre, "rt-soir", bloc="seance")
        seuil = self.SEANCES["seuil_fatigue"]
        k = self.mem["seance"]["op"]
        f = 0
        while self.i < fin_ops:
            if self.interruption(fin_ops):
                continue
            if k < len(s["ops"]):
                op = copy.deepcopy(s["ops"][k])
                k += 1
            elif f < len(s.get("facultatifs", [])):
                if self.sim.besoins["energie"] < seuil and s.get("fatigue"):
                    op = copy.deepcopy(s["fatigue"])
                    self.decisions.append(f"{hm(self.i)} : fatigue (énergie {round(self.sim.besoins['energie'], 1)}) ; séance écourtée.")
                    op.update({"piece": "atelier", "mode": "loisir"})
                    self.emettre(op, titre, "rt-soir", bloc="seance")
                    break
                op = copy.deepcopy(s["facultatifs"][f])
                f += 1
            else:
                break
            op.update({"piece": "atelier", "mode": "loisir"})
            self.emettre(op, titre, "rt-soir", bloc="seance")
        if k >= len(s["ops"]):
            self.faits.append(f"Séance {s['numero']} sur l'axe : {s['titre'].split(' : ')[1].split(' (')[0]}")
            self.mem["seance"] = {"numero": s["numero"] + 1, "op": 0}
        else:
            self.mem["seance"]["op"] = k
        # fermeture
        def lunettes(kk, pas):
            if kk == 1:
                self.poser_lunettes(pas)
        self.bloc("rangement_seance", remplace=lunettes)

    def coucher(self):
        fatigue = self.sim.besoins["energie"] < self.SEANCES["seuil_fatigue"]
        cible = idx(self.R["extinction_cible"])
        T = "Coucher"
        self.emettre({"action": "Se déshabille, range ses vêtements et pose sa montre sur la table de chevet.", "piece": "chambre",
                      "charge": "repos", "posture": "debout",
                      "objets": [{"objet": "obj-montre-poignet", "de": "poignet gauche", "vers": "chambre / table de chevet"}]}, T, "rt-soir")
        carnet = self.texte_carnet()
        livre = self.sim.positions["obj-livre"]
        if self.i >= cible:
            self.emettre({"action": "Se couche, écrit dans son carnet et le repose sous le livre.", "piece": "chambre", "charge": "repos",
                          "posture": "assis", "ev": ["ecriture_carnet"], "pensee": carnet,
                          "objets": [{"objet": "obj-carnet", "de": "chambre / table de chevet, sous le livre", "vers": "dans sa main"},
                                     {"objet": "obj-carnet", "de": "dans sa main", "vers": "chambre / table de chevet, sous le livre"}]}, T, "rt-soir")
            return
        if livre != "chambre / table de chevet" and not fatigue:
            piece_livre = livre.split(" / ")[0]
            self.emettre({"action": "S'aperçoit que son livre est resté ailleurs et va le chercher.", "piece": "chambre", "charge": "repos",
                          "posture": "debout", "via": [piece_livre], "ev": ["oubli_mineur"], "pensee": "Le livre. Toujours là où je ne suis pas.",
                          "objets": [{"objet": "obj-livre", "de": livre, "vers": "chambre / table de chevet"}]}, T, "rt-soir")
            self.mem["habitudes"]["ranger_livre"] = True
            self.decisions.append(f"{hm(self.i - 1)} : livre oublié hors de la chambre ; il le rangera désormais après chaque lecture.")
        lecture = {"action": "Se couche et lit (page {page}).", "piece": "chambre", "mode": "lecture", "charge": "lecture", "posture": "allongé"}
        prend = {"action": "Prend son carnet noir et écrit.", "piece": "chambre", "charge": "repos", "posture": "assis", "ev": ["ecriture_carnet"],
                 "pensee": carnet, "objets": [{"objet": "obj-carnet", "de": "chambre / table de chevet, sous le livre", "vers": "dans sa main"}]}
        repose = {"action": "Repose le carnet sous le livre et relit quelques pages (page {page}).", "piece": "chambre", "mode": "lecture",
                  "charge": "lecture", "posture": "allongé",
                  "objets": [{"objet": "obj-carnet", "de": "dans sa main", "vers": "chambre / table de chevet, sous le livre"}]}
        if fatigue:
            prend["action"] = "Se couche, prend son carnet et écrit."
            repose["action"] = "Repose le carnet sous le livre et lit deux pages (page {page})."
            self.emettre(prend, T, "rt-soir")
            self.emettre(repose, T, "rt-soir")
            return
        reste = cible - self.i
        suite = [lecture] * max(0, reste - 3) + [prend, repose, dict(lecture, action="Lit encore (page {page}).")]
        for p in suite[-reste:] if reste >= 3 else [prend, repose][:reste]:
            self.emettre(copy.deepcopy(p), T, "rt-soir")

    def endormissement(self):
        T = "Endormissement"
        demain = JOURS[(JOURS.index(self.jour) + 1) % 7]
        seance = self.seance_du_soir()
        nom_seance = seance["titre"].split(" : ")[1].split(" (")[0] if seance else "la montre"
        if demain in self.R["jours_course"]:
            txt = choix(self.PENSEES["extinction"]["course"], self.date, self.i)
        elif seance:
            txt = choix(self.PENSEES["extinction"]["seance"], self.date, self.i).replace("{seance}", nom_seance.capitalize())
        else:
            txt = choix(self.PENSEES["extinction"]["neutre"], self.date, self.i)
        ext = {"action": "Éteint la lumière.", "piece": "chambre", "charge": "repos", "posture": "allongé", "pensee": txt,
               "app": {"eteint": ["lumiere-chambre"]}}
        if self.sim.emo["excitation"] > 0.45:
            ext["ev"] = ["souvenir_excitant"]
        e = self.emettre(ext, T, "rt-soir")
        self.j.extinction = e["heure"]
        latence = self.sim.latence_endormissement(e["emotions"])
        self.j.endormissement = latence
        if latence > self.fiche["sante"]["sommeil"]["endormissement_minutes_normal"]:
            self.decisions.append(f"{e['heure']} : endormissement en {latence} minutes (anxiété {e['emotions']['anxiete']}, excitation {e['emotions']['excitation']}).")
        n = latence // 5 - 1
        for k in range(n):
            p = {"action": "Les yeux ouverts dans le noir." if k < n - 1 else "S'endort.", "piece": "chambre", "charge": "repos" if k < n - 1 else "sommeil",
                 "posture": "allongé"}
            if k == 0:
                if self.sim.emo["excitation"] > 0.4:
                    p["ev"] = ["souvenir_excitant"]
                    p["pensee"] = choix(self.PENSEES["endormissement"]["excitation"], self.date, self.i)
                elif seance and seance.get("delicate"):
                    p["ev"] = ["anticipation_delicate"]
                    p["pensee"] = choix(self.PENSEES["endormissement"]["anticipation"], self.date, self.i).replace("{seance}", nom_seance.capitalize())
                else:
                    p["pensee"] = choix(self.PENSEES["endormissement"]["neutre"], self.date, self.i)
            elif k < n - 1:
                p["action"] = "Ses pensées ralentissent."
            self.emettre(p, T, "rt-soir")
        debut = self.i
        while self.i < PAS_PAR_JOUR:
            m = (self.i - debut) * 5
            self.emettre({"action": "Dort.", "piece": "chambre", "mode": "sommeil", "charge": "sommeil", "posture": "allongé",
                          "phase_sommeil": phase_sommeil(m)}, "Sommeil", "sommeil", bloc="sommeil")
        self.mem["endormi_a"] = debut - PAS_PAR_JOUR

    def texte_carnet(self):
        faits = ". ".join(self.faits) + "." if self.faits else "Rien de particulier."
        return self.PENSEES["carnet"].replace("{jour}", self.jour.capitalize()).replace("{date}", self.date_txt).replace("{faits}", faits)

    def soiree(self):
        special = self.R["soirees_speciales"].get(self.date)
        if special and special["type"] == "lessive_match":
            self.bloc("lessive")
            self.seance(special["seance_fin_operations"])
            self.bloc("etendage")
            self.bloc("diner_match")
            self.bloc("match_premiere_mi_temps")
            self.bloc("mi_temps")
            self.bloc("match_seconde_mi_temps")
            self.bloc("qualification")
            self.faits.append("Real 1, Lyon 1 : qualifiés")
            self.mem["poubelle"]["repas"] += 1
            self.bloc("avant_coucher_match")
        else:
            debut_diner = idx(self.R["diner_fini_a"]) - self.longueur_diner()
            self.temps_libre(debut_diner)
            self.diner()
            self.seance(self.R["seance"]["fin"])
            self.bloc("chocolat")
            self.bloc("toilette_soir")
        self.coucher()
        self.endormissement()

    # ------------------------------------------------------------ outils du week-end
    def remplir(self, jusqua, pas, titre, routine):
        """Répète une activité tranquille jusqu'à l'heure indiquée."""
        jusqua = idx(jusqua) if isinstance(jusqua, str) else jusqua
        while self.i < jusqua:
            if self.interruption(jusqua):
                continue
            self.emettre(copy.deepcopy(pas), titre, routine, bloc="remplir_" + titre)

    def lecture_session(self, fin, routine):
        """Va chercher le livre, lit au séjour, et le rapporte (habitude apprise)."""
        fin = idx(fin) if isinstance(fin, str) else fin
        if self.mem.get("livre_termine"):
            return self.musique_session(fin, routine)
        self.bloc("repos_chambre")
        while self.i < fin - 1:
            if self.interruption(fin - 1):
                continue
            if self.mem.get("livre_termine"):
                p = {"action": "Reste allongé, le livre refermé sur la poitrine.", "piece": "sejour", "charge": "repos", "posture": "allongé"}
            else:
                p = {"action": "Lit sur le canapé (page {page}).", "piece": "sejour", "mode": "lecture", "charge": "lecture", "posture": "allongé"}
            self.emettre(p, "Lecture", routine, bloc="lecture_session")
        self.bloc("rangement_livre")

    def musique_session(self, fin, routine):
        fin = idx(fin) if isinstance(fin, str) else fin
        M = self.BLOCS["musique"]["pas"]
        if fin - self.i < 3:
            return self.remplir(fin, {"action": "Reste assis sur le canapé.", "piece": "sejour", "charge": "repos", "posture": "assis"}, "Repos", routine)
        self.emettre(copy.deepcopy(M[0]), "Musique", routine, bloc="musique")
        while self.i < fin - 1:
            if self.interruption(fin - 1):
                continue
            self.emettre(copy.deepcopy(M[1]), "Musique", routine, bloc="musique")
        self.emettre(copy.deepcopy(M[2]), "Musique", routine, bloc="musique")

    def sieste_session(self, fin, routine):
        fin = idx(fin) if isinstance(fin, str) else fin
        S = self.BLOCS["sieste"]["pas"]
        self.emettre(copy.deepcopy(S[0]), "Sieste", routine, bloc="sieste")
        while self.i < fin - 1:
            self.emettre(copy.deepcopy(S[1]), "Sieste", routine, bloc="sieste")
        self.emettre(copy.deepcopy(S[2]), "Sieste", routine, bloc="sieste")

    def lever_weekend(self, bid):
        while self.i < idx(self.R["reveil_week_end"]["heure_max"]):
            if self.interruption(idx(self.R["reveil_week_end"]["heure_max"])):
                continue
            self.emettre({"action": "Somnole, sans se presser de se lever.", "piece": "chambre", "charge": "repos", "posture": "allongé"},
                         "Grasse matinée", "rt-samedi", bloc="grasse_matinee")
        self.bloc(bid)

    def repas_midi_weekend(self):
        r = self.REPAS["midi"][self.jour]
        for k, p in enumerate(r["repas"]):
            self.emettre(copy.deepcopy(p), "Déjeuner", "rt-samedi", bloc="dejeuner", k=k)
        for k, p in enumerate(r.get("apres") or []):
            self.emettre(copy.deepcopy(p), "Café et vaisselle", "rt-samedi", bloc="apres_dejeuner", k=k)
        self.mem["poubelle"]["repas"] += 1

    def soiree_weekend(self, moment_montre=None):
        debut_diner = idx(self.R["diner_fini_a"]) - self.longueur_diner()
        self.temps_libre(debut_diner)
        self.diner()
        fin = idx(self.R[self.jour]["soiree_libre_jusqua"])
        if moment_montre:
            self.lecture_session(moment_montre, "rt-soir") if not self.mem.get("livre_termine") else self.musique_session(moment_montre, "rt-soir")
            self.emettre({"action": "Va voir la montre de gousset à l'atelier : elle tourne toujours. Il l'écoute un moment.", "piece": "atelier",
                          "charge": "repos", "posture": "debout", "ev": ["souvenir_grand_pere"]}, "La montre tourne", "rt-soir", bloc="montre")
        R = self.BLOCS["radio_soir"]["pas"]
        self.emettre(copy.deepcopy(R[0]), "Radio", "rt-soir", bloc="radio")
        while self.i < fin - 1:
            if self.interruption(fin - 1):
                continue
            self.emettre(copy.deepcopy(R[1]), "Radio", "rt-soir", bloc="radio")
        self.emettre(copy.deepcopy(R[2]), "Radio", "rt-soir", bloc="radio")
        self.bloc("chocolat")
        self.bloc("toilette_soir")
        self.coucher()
        self.endormissement()

    # ------------------------------------------------------------ samedi et dimanche
    def samedi(self, reveil):
        S = self.R["samedi"]
        self.lever_weekend("reveil_weekend")
        self.bloc("toilettes_matin")
        self.bloc("petit_dejeuner_long")
        self.remplir(S["douche"], {"action": "Écoute la radio au séjour.", "piece": "sejour", "charge": "repos", "posture": "assis", "radio": True},
                     "Radio", "rt-samedi")
        self.bloc("douche_rasage_weekend")
        self.bloc("habillage_weekend")
        self.bloc("menage")
        self.lecture_session(S["lecture"][1], "rt-samedi")
        self.repas_midi_weekend()
        self.sieste_session(S["sieste"][1], "rt-samedi")
        self.seance(hm(idx(S["seance"][1]) - 2))
        self.musique_session(S["musique"][1], "rt-samedi")
        self.soiree_weekend(moment_montre=idx(S["regarder_la_montre"]))

    def dimanche(self, reveil):
        D = self.R["dimanche"]
        self.lever_weekend("reveil_dimanche")
        self.bloc("toilettes_matin")
        self.tenue_course()
        def boire(k, pas):
            if self.sim.besoins["soif"] - 0.7 < 60:
                pas["effets"] = {"soif": 20}
                pas["action"] += " Boit encore un verre d'eau."
        self.bloc("etirements_course", remplace=boire)
        self.depart_course()
        pb = self.mem["poubelle"]
        def sac(k, pas):
            if k == 0:
                if pb.get("en_main"):
                    pas["objets"] = [{"objet": pb["en_main"], "de": "dans sa main", "vers": "local poubelles de l'immeuble"}]
                else:
                    pas.pop("objets", None)
                    pas["action"] = pas["action"].replace(", dépose le sac au local poubelles", "")
        self.bloc("descente_saone", remplace=sac)
        pb.pop("en_main", None)
        Q = self.BLOCS["quais_saone"]
        for k in range(D["quais_pas"]):
            p = copy.deepcopy(Q["pas"][k % len(Q["pas"])])
            p["parcours"] = [{"moyen": "course", "distance_m": D["quais_distance_m"], "denivele_m": 0}]
            p["action"] = "Fait demi-tour au bout de la boucle longue." if k == D["quais_pas"] // 2 else \
                ("Rejoint le bord de l'eau et prend son rythme vers le nord." if k == 0 else "Court le long de la Saône, sortie longue.")
            self.emettre(p, "Sortie longue le long de la Saône", "rt-dimanche", bloc="quais_saone", k=k)
        R = self.BLOCS["remontee_pentes"]
        for k, dist in enumerate(D["remontee_marche"]):
            p = copy.deepcopy(R["pas"][min(k, len(R["pas"]) - 1)])
            p["parcours"] = [{"moyen": "marche", "distance_m": dist, "denivele_m": [28, 28, 29][k]}]
            p["posture"] = "en marche"
            p["action"] = ["Remonte les pentes en marchant, les jambes lourdes.", "Continue la montée à pied.", "Termine la montée et reprend son souffle."][k]
            self.emettre(p, "Remontée à pied", "rt-dimanche", bloc="remontee", k=k)
        self.bloc("retour_course")
        self.faits.append("Sortie longue : 12 km")
        def sans_rasage(k, pas):
            if k == 2:
                pas["action"] = "Se sèche et se masse les mollets."
        self.bloc("douche_course", remplace=sans_rasage)
        self.bloc("habillage")
        self.remplir(D["brunch"], {"action": "S'assoit un moment, les jambes lourdes, un verre d'eau à la main.", "piece": "sejour",
                                   "charge": "repos", "posture": "assis", "effets": {"soif": 10}}, "Repos", "rt-dimanche")
        self.bloc("brunch")
        self.mem["poubelle"]["repas"] += 1
        self.lecture_session(D["sieste"][0], "rt-dimanche")
        self.sieste_session(D["sieste"][1], "rt-dimanche")
        self.musique_session(D["seance"][0], "rt-dimanche")
        self.seance(hm(idx(D["seance"][1]) - 2))
        self.bloc("planification")
        self.musique_session(D["musique"][1], "rt-dimanche")
        self.soiree_weekend()

    # ------------------------------------------------------------ journée
    def vivre(self):
        self.mem["courant"] = None
        self.mem["intercale"] = None
        reveil = self.nuit()
        if self.jour == "samedi":
            self.samedi(reveil)
            return self.terminer()
        if self.jour == "dimanche":
            self.dimanche(reveil)
            return self.terminer()
        self.matin(reveil)
        A = self.R["atelier"]
        def lunettes(k, pas):
            self.poser_lunettes(pas)
        self.atelier(A[0]["debut"], A[0]["fin"])
        self.bloc("pause_wc", remplace=lunettes)
        self.bloc("pause_cafe")
        self.atelier(A[1]["debut"], A[1]["fin"], fin_de_seance=True, avance=self.avance_dejeuner())
        self.dejeuner()
        self.repos()
        self.atelier(A[2]["debut"], A[2]["fin"])
        self.bloc("pause_wc", remplace=lunettes)
        self.pause_fruit()
        self.atelier(A[3]["debut"], A[3]["fin"])
        self.rangement_atelier()
        self.soiree()
        return self.terminer()

    def terminer(self):
        if self.i != PAS_PAR_JOUR:
            raise Incoherence(f"la journée de l'agent compte {self.i} pas")
        etat_final, stats = self.sim.terminer(self.j.extinction, self.j.endormissement)
        self.mem.pop("evocations_du_jour", None)
        etat_final["agent"] = self.mem
        self.j.ecarts = self.decisions
        self.j.resume = {"travaux": self.resume_travaux()}
        self.j.bilan = [f"**{f}**" for f in self.faits] or ["Journée sans fait marquant."]
        for s in self.j.segments:
            s.pop("_bloc", None)
        return self.sim.steps, etat_final, stats

    def resume_travaux(self):
        out = {}
        for t in self.TRAVAUX["liste"]:
            m = self.mem["travaux"][t["id"]]
            restant = sum(len(ph.get("ops", [])) for ph in t["phases"][m["phase"]:]) - m["op"]
            if m["termine"]:
                out[t["id"]] = "terminé"
            elif m["dispo"] and m["dispo"] > self.abs():
                out[t["id"]] = f"en attente jusqu'au pas {m['dispo'] % PAS_PAR_JOUR} ({hm(m['dispo'] % PAS_PAR_JOUR)}) du jour {m['dispo'] // PAS_PAR_JOUR + 1} ; {restant} opérations restantes"
            else:
                out[t["id"]] = f"{restant} opérations restantes"
        return out
