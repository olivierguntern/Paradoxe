"""Agent autonome d'un commerçant : Robert Chazal, l'épicier de la Grande-Rue.

L'agent fait vivre Robert pas à pas à partir de ses scènes (data/agents/
robert-chazal/blocs.json, reprises de ses journées de référence ou rédigées
pour la fin de semaine), de ses règles (regles.json) et de ses pensées
(pensees.json). Il lit son état dans la simulation à chaque pas.

Principales décisions :
- horaires de la boutique, livraisons du pain et du grossiste, commande du
  lundi et du jeudi soir calculée d'après le stock du magasin ;
- au comptoir : clients du flux déterministe (outils/clientele.py), visites
  de Thomas Berthier lues dans sa journée, ruptures de stock, café à heures
  fixes, toilettes et eau quand un besoin passe sous son seuil, Le Progrès,
  bavardage avec le buraliste, les Grosses Têtes à la radio ;
- caisse du midi et du soir rangée au coffre ; dépôt à la banque le lundi ;
- courses de la maison prélevées au magasin selon les repas de Josiane et ses
  propres provisions ; cabas oublié après une nuit trop courte ;
- soirées : télévision écourtée par la fatigue, match, belote, cinéma ;
  le dimanche, vote et randonnée ; endormissement selon l'excitation.
"""
import copy
import datetime
import json
import math
import os

from agent import JOURS, MOIS, choix, phase_sommeil, tirage
from clientele import Comptoir, enumerer, euros, libelle
from moteur import PAS_PAR_JOUR, Incoherence, Journee, Simulation, hm, idx

BOUTIQUE, TRAJET, KANGOO = "epicerie-chazal", "trajet-voiture", "Kangoo"
ARRIVEE_BOUTIQUE = [("obj-kangoo", "cour-epicerie / place louée"), ("obj-cles-kangoo", "poche de la blouse"), ("obj-veste", "arriere-boutique / patère"),
                    ("obj-blouse", "porté"), ("obj-cles", "poche de la blouse")]
DEPART_BOUTIQUE = [("obj-blouse", "arriere-boutique / patère"), ("obj-veste", "porté"), ("obj-cles", "poche de la veste"),
                   ("obj-cles-kangoo", "contact de la Kangoo"), ("obj-kangoo", "en route")]
ARRIVEE_MAISON = [("obj-kangoo", "garage / place de la Kangoo"), ("obj-cles-kangoo", "entree / vide-poche"), ("obj-cles", "entree / vide-poche"),
                  ("obj-portefeuille", "entree / vide-poche"), ("obj-veste", "entree / portemanteau")]
DEPART_MAISON = [("obj-veste", "porté"), ("obj-cles", "poche de la veste"), ("obj-cles-kangoo", "dans sa main"), ("obj-portefeuille", "poche de la veste")]
CABAS = "obj-cabas-boutique"


class AgentEpicier:
    def __init__(self, fiche, dossier, date, etat):
        self.fiche = fiche
        self.R = json.load(open(os.path.join(dossier, "regles.json")))
        self.B = json.load(open(os.path.join(dossier, "blocs.json")))
        self.P = json.load(open(os.path.join(dossier, "pensees.json")))
        self.racine = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(dossier))))
        self.C = fiche["commerce"]
        self.CAT = {c["produit"]: c for c in self.C["catalogue"]}
        self.ECHANGES = json.load(open(os.path.join(self.racine, "data", "monde", "echanges.json")))[self.C["id"]]
        self.MONDE_EV = json.load(open(os.path.join(self.racine, "data", "monde", "evenements.json")))
        self.PROV = {x["id"]: x for x in fiche["domicile"]["provisions_au_debut"]}
        self.MENUS = fiche["menus_prevus"]
        self.date = date
        d = datetime.date.fromisoformat(date)
        self.d = d
        self.jour = JOURS[d.weekday()]
        self.sim = Simulation(fiche, date, etat)
        self.sans_courses = False
        self.mem = copy.deepcopy(etat.get("agent")) or self.memoire_initiale()
        self.mem["jour_index"] = self.mem.get("jour_index", -1) + 1
        self.mem["evocations_du_jour"] = {}
        self.j = Journee(date, self.jour, extinction="22:30")
        self.j.methode = [
            "Généré par l'agent autonome du commerçant (outils/agent_epicier.py) à partir de ses scènes, règles et pensées (data/agents/robert-chazal/).",
            "Clients anonymes du flux déterministe de outils/clientele.py ; visites de Thomas Berthier lues dans sa propre journée.",
            "Calculé par outils/moteur.py avec les règles de la fiche : déplacements, lumière, besoins, émotions, stock du magasin, caisse.",
            "La journée part de l'état exact de la fin de la veille.",
        ]
        self.faits, self.decisions = [], []
        self.PIECES = {pc["id"]: pc for pc in fiche["domicile"]["pieces"]}
        self.comptoir = Comptoir(fiche, date, self.jour, {}, self.mem["ardoises"])
        self.recette = 0.0
        self.faits_comptoir = set()
        self.visites = self.lire_visites()
        self.fond = fiche["economie"]["caisse_au_debut"]

    # ------------------------------------------------------------ mémoire
    def memoire_initiale(self):
        # le bon de commande de mardi a été écrit dimanche à la fermeture, avant la période : stock du magasin ramené à sa cible
        commande = {p: c["cible"] - self.sim.boutique.get(p, 0) for p, c in self.CAT.items() if not c.get("frais") and c["cible"] > self.sim.boutique.get(p, 0)}
        return {"endormi_a": idx(self.R["endormi_la_veille_du_premier_jour"]) - PAS_PAR_JOUR, "commande": commande, "ardoises": {},
                "journal": None, "journal_veille": None, "evocations": {}, "nuit_minutes": None, "recettes": {}}

    @property
    def i(self):
        return len(self.sim.steps)

    def abs(self):
        return self.mem["jour_index"] * PAS_PAR_JOUR + self.i

    def lire_visites(self):
        """Pas où le client simulé est dans la boutique, avec ses achats et son paiement."""
        chemin = os.path.join(self.racine, "data", "timelines", self.R["client"], f"{self.date}.json")
        if not os.path.exists(chemin):
            return {}
        return {s["pas"]: s for s in json.load(open(chemin))["pas"] if s.get("lieu") == self.C["id"]}

    # ------------------------------------------------------------ émission
    def lieu_de(self, piece):
        pc = self.PIECES.get(piece)
        if pc:
            return BOUTIQUE if pc.get("lieu") == "epicerie" else "domicile"
        return "domicile" if piece in ("jardin", "rue-maison") else ("exterieur" if piece == "trottoir" else "domicile")

    def resoudre(self, spec):
        """Complète un pas de scène : objets déplacés depuis leur position actuelle, journal du jour, repas du menu."""
        st = copy.deepcopy(spec)
        for cle in ("role", "modele", "modele_vide", "modele_pensee", "modele_rien"):
            st.pop(cle, None)
        noms = {"JOURNAL": self.mem.get("journal"), "JOURNAL_VEILLE": self.mem.get("journal_veille")}
        objets = []
        for o in st.pop("objets", []):
            oid, vers = (o["objet"], o["vers"]) if isinstance(o, dict) else o
            oid = noms.get(oid, oid)
            if not oid or oid not in self.sim.positions:
                continue
            de = self.sim.positions[oid]
            if de != vers and not any(x["objet"] == oid for x in objets):
                objets.append({"objet": oid, "de": de, "vers": vers})
            elif any(x["objet"] == oid for x in objets):
                prec = next(x for x in objets if x["objet"] == oid)
                if prec["vers"] != vers:
                    objets.append({"objet": oid, "de": prec["vers"], "vers": vers})
        if objets:
            st["objets"] = objets
        repas = st.pop("repas", None)
        if repas:
            st["consommation"] = self.consommation_repas(repas)
        elif st.get("consommation"):
            st["consommation"] = [{"produit": p, "quantite": q} if not isinstance(p, dict) else p for p, q in st["consommation"]] \
                if isinstance(st["consommation"][0], list) else st["consommation"]
        return st

    def emettre(self, spec, titre=None, routine=None, bloc=None):
        st = self.resoudre(spec)
        titre = st.pop("titre", None) or titre
        routine = st.pop("routine", None) or routine
        piece = st.pop("piece", self.sim.piece)
        s = {"titre": titre, "routine": routine, "piece": piece, "lieu": st.pop("lieu", None) or self.lieu_de(piece),
             "mode": st.pop("mode", "eveille"), "charge": st.pop("charge", "simple"), "posture": st.pop("posture", "debout")}
        st.setdefault("pensee", None)
        st.setdefault("action", "")
        entree = self.sim.pas(st, s)
        segs = self.j.segments
        cle = bloc or titre
        if segs and segs[-1]["titre"] == titre and segs[-1].get("_bloc") == cle:
            segs[-1]["pas"].append(st)
        else:
            segs.append({"debut": hm(entree["pas"]), "titre": titre, "routine": routine, "piece": s["piece"], "pas": [st], "_bloc": cle})
        for v in entree.get("ventes", []):
            self.recette = round(self.recette + v["prix"], 2)
        return entree

    def scene(self, nom, variante=None):
        """Les pas d'une scène, dans la variante du jour s'il y en a une."""
        b = self.B[nom]
        return copy.deepcopy(b.get(variante or self.jour) or b["defaut"])

    def jouer(self, nom, variante=None, fmt=None):
        for spec in self.scene(nom, variante):
            spec = self.appliquer_role(spec)
            if spec is None:
                continue
            if fmt:
                for k in ("action", "pensee"):
                    if spec.get(k) and "{" in spec[k]:
                        spec[k] = spec[k].format(**fmt)
            self.emettre(spec)

    def appliquer_role(self, spec):
        r = spec.get("role")
        if not r:
            return spec
        return getattr(self, "role_" + r)(spec)

    # ------------------------------------------------------------ outils de décision
    def heure(self, h):
        return idx(h)

    def preoccupation(self, st):
        """Ajoute parfois une pensée liée à la préoccupation la plus pesante."""
        if st.get("pensee") or tirage(self.date, self.i, "preoc") >= self.P["frequence_preoccupations"]:
            return st
        prs = {x["id"]: x for x in self.fiche["vie_interieure"]["preoccupations_semaine"]}
        meilleur, score = None, -1
        for pid, spec in self.P["preoccupations"].items():
            if spec.get("jusqua") and self.date > spec["jusqua"]:
                continue
            if self.mem["evocations_du_jour"].get(pid, 0) >= 2:
                continue
            depuis = self.abs() - self.mem["evocations"].get(pid, -10 ** 6)
            sc = prs[pid]["intensite_initiale"] * (1 + min(depuis, 2000) / 60)
            if sc > score:
                meilleur, score = pid, sc
        if meilleur:
            spec = self.P["preoccupations"][meilleur]
            st["pensee"] = choix(spec["textes"], self.date, self.i, meilleur)
            st.setdefault("ev", []).append(spec["evenement"])
            self.mem["evocations"][meilleur] = self.abs()
            self.mem["evocations_du_jour"][meilleur] = self.mem["evocations_du_jour"].get(meilleur, 0) + 1
        return st

    def consommation_repas(self, moment):
        repas = self.MENUS["petit_dejeuner"] if moment == "petit_dejeuner" else self.MENUS[self.jour][moment]
        out = []
        for pid, q in repas["ingredients"]:
            spec = self.PROV[pid]
            if spec.get("suivi", True):
                reste = self.sim.stock.get(pid, 0)
                if reste < q:
                    self.decisions.append(f"{hm(self.i)} : il ne reste que {reste} {spec['unite']} de {spec['produit']} ; Josiane fait avec.")
                    q = reste
            if q:
                out.append({"produit": pid, "quantite": q})
        return out

    # ------------------------------------------------------------ courses de la maison
    def repas_a_couvrir(self):
        """Repas pas encore mangés d'ici au premier repas qui suit le prochain départ de la boutique."""
        ordre = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        k = ordre.index(self.jour)
        midi = self.i < idx("13:00")
        out = []
        if self.jour == "lundi":
            out = []  # jour de congé : il ne passe à la boutique que pour la recette
        elif self.jour == "dimanche":
            # le lundi, il ne rapporte rien : le cabas du dimanche va jusqu'au déjeuner du mardi
            out = ([("dimanche", "dejeuner")] if midi else []) + [("dimanche", "diner"), ("lundi", "dejeuner"), ("lundi", "diner"), ("mardi", "dejeuner")]
        else:
            out = [(self.jour, "diner"), (ordre[(k + 1) % 7], "dejeuner")]
        return out

    def liste_cabas(self, pour_texte=False):
        """Prélèvements à faire au magasin : manques pour les repas, puis provisions personnelles sous leur seuil."""
        besoin = {}
        for jour, moment in self.repas_a_couvrir():
            for pid, q in self.MENUS[jour][moment]["ingredients"]:
                spec = self.PROV[pid]
                if pid == "pain" or not spec.get("magasin") or not spec.get("suivi", True):
                    continue
                besoin[pid] = besoin.get(pid, 0) + q
        prises = {}
        for pid, q in besoin.items():
            manque = q - self.sim.stock.get(pid, 0)
            if manque > 0:
                prises[pid] = math.ceil(manque / self.PROV[pid]["par_unite"])
        for pid, r in self.R["cabas"]["provisions_personnelles"].items():
            if self.sim.stock.get(pid, 0) < r["seuil"] and pid not in prises:
                prises[pid] = r["unites"]
        lignes, manques = [], []
        for pid, n in prises.items():
            prod = self.R["cabas"]["provisions_personnelles"].get(pid, {}).get("produit") or self.PROV[pid]["magasin"]
            dispo = self.sim.boutique.get(prod, 0)
            if dispo < n:
                manques.append(self.CAT[prod]["nom"].split(" (")[0])
                n = dispo
            if n:
                lignes.append({"produit": prod, "quantite": n, "maison": pid, "quantite_maison": n * self.PROV[pid]["par_unite"]})
        return lignes, manques

    def texte_cabas(self, lignes):
        return enumerer([libelle(self.CAT[x["produit"]], x["quantite"]) for x in lignes]) if lignes else ""

    # ------------------------------------------------------------ rôles des scènes
    def role_depart_maison(self, spec):
        objets = [list(x) for x in DEPART_MAISON]
        matin = self.i < idx("08:00")
        cabas = self.sim.positions.get(CABAS) == "entree / portemanteau"
        oubli = False
        if cabas and matin:
            nuit = self.mem.get("nuit_minutes")
            if nuit is not None and nuit < self.R["cabas"]["oubli_si_nuit_de_moins_de_minutes"]:
                oubli = True
                self.decisions.append(f"{hm(self.i)} : après une nuit de {nuit // 60} h {nuit % 60:02d}, il oublie le cabas au portemanteau.")
        if cabas and not oubli:
            objets.append([CABAS, "dans sa main"])
        if matin:
            spec["action"] = ("Prend sa veste, ses clés, celles de la Kangoo" + (", son portefeuille et le cabas vide au portemanteau" if cabas and not oubli
                                                                                 else " et son portefeuille") +
                              ". Ouvre la porte basculante." + (" Le cabas reste accroché au portemanteau." if oubli else ""))
        elif cabas:
            spec["action"] += " Prend aussi le cabas accroché au portemanteau."
            self.decisions.append(f"{hm(self.i)} : voit le cabas au portemanteau et le reprend pour la boutique.")
        spec["objets"] = objets
        return spec

    def role_arrivee_boutique(self, spec):
        objets = [list(x) for x in ARRIVEE_BOUTIQUE]
        if self.sim.positions.get(CABAS) == "dans sa main":
            objets.append([CABAS, "arriere-boutique / patère"])
        spec["objets"] = objets
        spec["retour"] = "cour-epicerie"
        return spec

    def role_arrivee_maison(self, spec):
        objets = [list(x) for x in ARRIVEE_MAISON]
        pos = self.sim.positions
        if pos.get(CABAS) == "dans sa main":
            objets.append([CABAS, "entree / portemanteau"])
        carton = self.mem.get("carton")
        if carton and pos.get(carton) == "dans sa main":
            objets.append([carton, "garage / pile de cartons"])
        jl = self.mem.get("journal")
        if jl and pos.get(jl) in ("dans le cabas", "sous son bras", "dans le carton"):
            objets.append([jl, "cuisine / table"])
        spec["objets"] = objets
        spec["retour"] = "garage"
        return spec

    role_arrivee_soir = role_arrivee_maison

    def role_pain(self, spec):
        L = self.C["livraisons"]["pain"]
        pain = {k: L[k].get(self.jour, L[k]["defaut"]) for k in ("baguette", "pain_campagne")}
        invendus = {k: self.sim.boutique.get(k, 0) for k in pain}
        n = self.R["pain_mis_de_cote"].get(self.jour, self.R["pain_mis_de_cote"]["defaut"])
        spec["livraisons"] = [{"produit": k, "quantite": q} for k, q in pain.items()]
        spec["reprises"] = [{"produit": k, "quantite": q, "motif": "invendus de la veille repris par le livreur"} for k, q in invendus.items() if q]
        spec["prelevements"] = [{"produit": "baguette", "quantite": n, "maison": "pain", "quantite_maison": n * self.PROV["pain"]["par_unite"]}]
        cb = self.R["cabas"]["cafe_boutique"]
        txt_cafe = ""
        if self.sim.stock.get("cafe_boutique", 0) < cb["seuil"]:
            spec["prelevements"].append({"produit": "cafe_moulu", "quantite": cb["unites"], "maison": "cafe_boutique",
                                         "quantite_maison": cb["unites"] * self.PROV["cafe_boutique"]["par_unite"]})
            txt_cafe = " Prend aussi un paquet de café pour la cafetière de l'arrière-boutique."
            self.decisions.append(f"{hm(self.i)} : le café de l'arrière-boutique baisse ; il en prend un paquet au rayon.")
        rep = sum(invendus.values())
        spec["action"] = spec["modele"].format(
            pain=enumerer([libelle(self.CAT[k], q) for k, q in pain.items()]),
            reprise=(f" ; il reprend {libelle(self.CAT['baguette'], invendus['baguette']) if invendus['baguette'] else ''}"
                     f"{' et ' if invendus['baguette'] and invendus['pain_campagne'] else ''}"
                     f"{libelle(self.CAT['pain_campagne'], invendus['pain_campagne']) if invendus['pain_campagne'] else ''} d'hier") if rep else "",
            mis_de_cote="une baguette" if n == 1 else "deux baguettes") + txt_cafe
        jl = f"obj-progres-{self.date[5:7]}{self.date[8:10]}"
        self.mem["journal_veille"], self.mem["journal"] = self.mem.get("journal"), jl
        spec["nouveaux_objets"] = [{"id": jl, "nom": f"Le Progrès du {self.jour} {self.d.day} {MOIS[self.d.month - 1]} {self.d.year}", "position": "boutique / comptoir"}]
        return spec

    def role_journal_josiane(self, spec):
        jl = f"obj-progres-{self.date[5:7]}{self.date[8:10]}"
        self.mem["journal_veille"], self.mem["journal"] = self.mem.get("journal"), jl
        spec["nouveaux_objets"] = [{"id": jl, "nom": f"Le Progrès du {self.jour} {self.d.day} {MOIS[self.d.month - 1]} {self.d.year}", "position": "cuisine / table"}]
        return spec

    def role_grossiste(self, spec):
        commande = self.mem.get("commande") or {}
        spec["livraisons"] = [{"produit": p, "quantite": q} for p, q in commande.items() if q]
        spec["pensee"] = spec.get("modele_pensee", "{n_commande} lignes.").format(n_commande=len(spec["livraisons"]))
        self.faits.append(f"Livraison du grossiste : {len(spec['livraisons'])} lignes")
        self.mem["commande"] = None
        return spec

    def caisse(self, spec, soir):
        especes = round(self.sim.argent.get("caisse", 0) - self.fond, 2)
        spec["argent"] = {"caisse": -especes, "coffre": especes}
        tasse = [["obj-tasse-boutique", "arriere-boutique / évier"]] if self.sim.positions.get("obj-tasse-boutique") == "boutique / comptoir" else []
        spec["objets"] = tasse
        if not tasse:
            spec["modele"] = spec["modele"].replace(" Rince la tasse de Lucas.", "").replace(" Rince la tasse.", "")
        if soir:
            obj = self.R["objectif_recette_eur"]
            spec["action"] = spec["modele"].format(especes=euros(especes), recette_jour=euros(self.recette))
            spec["pensee"] = self.P["caisse"]["dessus" if self.recette >= obj else "dessous"]
            spec["ev"] = ["caisse_juste"] + (["constat_chiffre"] if self.recette < obj else [])
            self.faits.append(f"Recette : {euros(self.recette)} ({self.comptoir.nb_clients} clients)")
        else:
            spec["action"] = spec["modele"].format(especes=euros(especes))
            spec["pensee"] = self.P["caisse"]["midi"].format(recette=euros(self.recette))
        return spec

    def role_caisse_midi(self, spec):
        return self.caisse(spec, soir=False)

    def role_caisse_soir(self, spec):
        return self.caisse(spec, soir=True)

    def role_cabas_soir(self, spec):
        lignes, manques = self.liste_cabas()
        pos = self.sim.positions
        jl = self.mem.get("journal")
        if not lignes:
            spec["action"] = spec["modele_vide"]
            spec.pop("pensee", None)
            spec["objets"] = [[jl, "sous son bras"]] if jl and pos.get(jl) == "boutique / comptoir" else []
            self.decisions.append(f"{hm(self.i)} : rien à rapporter pour la maison.")
            return spec
        if pos.get(CABAS) == "arriere-boutique / patère":
            contenant, objets = "le cabas de la boutique", [[CABAS, "dans sa main"]]
            ou = "dans le cabas"
        else:
            carton = f"obj-carton-{self.date[5:7]}{self.date[8:10]}"
            self.mem["carton"] = carton
            spec["nouveaux_objets"] = [{"id": carton, "nom": "Carton vide de la réserve, pour rapporter les courses de la maison", "position": "dans sa main"}]
            contenant, objets, ou = "un carton vide de la réserve, faute de cabas,", [], "dans le carton"
            spec["ev"] = spec.get("ev", []) + ["petit_oubli"]
            spec["pensee"] = "Le cabas, je l'ai laissé à la maison ce matin. Ça m'apprendra."
        if jl and pos.get(jl) == "boutique / comptoir":
            objets.append([jl, ou])
        spec["prelevements"] = lignes
        txt = self.texte_cabas(lignes)
        spec["action"] = spec["modele"].format(contenant=contenant, liste=txt)
        if manques:
            spec["action"] += f" Plus de {enumerer(manques)} en rayon : Josiane fera sans."
            self.decisions.append(f"{hm(self.i)} : plus de {enumerer(manques)} au magasin pour la maison.")
        if ou != "dans le carton":
            spec["pensee"] = (spec.get("modele_pensee") or "{liste_courte}.").format(liste_courte=", ".join(
                self.PROV[x["maison"]]["produit"].split(" (")[0].capitalize() if k == 0 else self.PROV[x["maison"]]["produit"].split(" (")[0]
                for k, x in enumerate(lignes)))
        spec["objets"] = objets
        self.decisions.append(f"{hm(self.i)} : rapporte pour la maison {txt}.")
        return spec

    def role_demande_josiane(self, spec):
        # ce qu'il faudra rapporter ce soir, vu d'ici
        lignes, _ = self.liste_cabas()
        plat = self.MENUS[self.jour]["diner"]["plat"].split(",")[0].split(" ;")[0]
        if lignes:
            spec["action"] = spec["modele"].format(plat_soir=plat, liste=self.texte_cabas(lignes))
            spec["pensee"] = spec["modele_pensee"].format(liste_courte=", ".join(self.PROV[x["maison"]]["produit"].split(" (")[0] for x in lignes).capitalize())
        else:
            spec["action"] = spec["modele_rien"].format(plat_soir=plat)
            spec.pop("pensee", None)
        return spec

    def role_commande_jeudi(self, spec):
        commande = {p: c["cible"] - self.sim.boutique.get(p, 0) for p, c in self.CAT.items() if not c.get("frais") and c["cible"] > self.sim.boutique.get(p, 0)}
        self.mem["commande"] = commande
        spec["action"] = spec["modele"].format(commande=self.texte_commande(commande), n_commande=len(commande))
        self.faits.append(f"Bon de commande pour vendredi : {len(commande)} lignes")
        return spec

    def texte_commande(self, commande, limite=5):
        items = [libelle(self.CAT[p], q) for p, q in commande.items() if q]
        if len(items) > limite:
            return enumerer(items[:limite] + [f"{len(items) - limite} autres produits"])
        return enumerer(items) if items else "rien"

    # rôles du lundi
    def role_banque_recette(self, spec):
        spec["action"] = spec["modele"].format(coffre=euros(self.sim.argent.get("coffre", 0)))
        return spec

    def role_depot(self, spec):
        m = self.sim.argent.get("coffre", 0)
        spec["argent"] = {"coffre": -m, "compte": m}
        self.faits.append(f"Recette de la semaine passée déposée au coffre de la banque : {euros(m)}")
        return spec

    def role_perimes(self, spec):
        perimes = {}
        for p, taux in self.R["perimes_au_menage"].items():
            if p == "principe":
                continue
            n = round(self.sim.boutique.get(p, 0) * taux)
            if n:
                perimes[p] = n
        spec["reprises"] = [{"produit": p, "quantite": q, "motif": "date dépassée ou abîmé, jeté"} for p, q in perimes.items()]
        spec["action"] = spec["modele"].format(perimes=enumerer([libelle(self.CAT[p], q) for p, q in perimes.items()]) or "rien")
        return spec

    # rôles de la fin de semaine (dimanche à la fermeture)
    def role_comptes_semaine(self, spec):
        debut = (self.d - datetime.timedelta(days=6)).isoformat()
        total = round(sum(v for d, v in (self.mem.get("recettes") or {}).items() if d >= debut) + self.recette, 2)
        spec["action"] = spec["modele"].format(semaine=euros(total))
        spec["pensee"] = spec["modele_pensee"].format(semaine=euros(total).capitalize())
        self.faits.append(f"Comptes de la semaine : {euros(total)}")
        return spec

    def role_commande_dimanche(self, spec):
        commande = {p: c["cible"] - self.sim.boutique.get(p, 0) for p, c in self.CAT.items() if not c.get("frais") and c["cible"] > self.sim.boutique.get(p, 0)}
        self.mem["commande"] = commande
        spec["action"] = spec["modele"].format(commande=self.texte_commande(commande))
        return spec

    def role_commande_fin(self, spec):
        n = len(self.mem.get("commande") or {})
        spec["action"] = spec["modele"].format(n_commande=n)
        self.faits.append(f"Bon de commande pour mardi : {n} lignes")
        return spec

    def role_journal_dimanche(self, spec):
        return spec

    def role_depart_vote(self, spec):
        return spec

    def role_debut_randonnee(self, spec):
        return spec

    def role_arrivee_randonnee(self, spec):
        spec["retour"] = "garage"
        return spec

    # ------------------------------------------------------------ nuit
    def nuit(self, reveil_i):
        titre = f"Nuit de {JOURS[(JOURS.index(self.jour) - 1) % 7]} à {self.jour}"
        debut = self.mem["endormi_a"]
        n_reve, ancienne = 0, None
        while self.i < reveil_i:
            phase = phase_sommeil((self.i - debut) * 5)
            st = {"action": "Dort." if phase != "micro-éveil" else choix(self.P["micro_eveil"], self.date, self.i), "piece": "chambre", "lieu": "domicile",
                  "mode": "sommeil", "charge": "sommeil", "posture": "allongé", "phase_sommeil": phase}
            if phase == "paradoxal" and ancienne != "paradoxal" and n_reve < 3:
                r = choix(self.P["reves"], self.date, self.i)
                st["reve"] = r["texte"]
                if r["ev"]:
                    st["ev"] = [r["ev"]]
                n_reve += 1
            self.emettre(st, titre, "sommeil", bloc="nuit")
            ancienne = phase
        self.mem["nuit_minutes"] = (reveil_i - debut) * 5

    # ------------------------------------------------------------ trajets
    def route(self, nom, decoupe, depart=None, arrivee=None, variante=None):
        """Trajet en Kangoo : un pas par tronçon de la découpe ; depart = « garage », « cour », « parking » ; arrivee = « parking »."""
        T = self.B["routes"][nom]
        t = T.get(variante or self.jour) or T["defaut"]
        D = self.R["trajets"][decoupe]
        titre = {"aube": "Route vers la Croix-Rousse", "midi": "Retour déjeuner", "apres_midi": "Retour à la boutique", "soir": "Retour à la maison",
                 "lundi_matin": "Route vers la Croix-Rousse", "lundi_midi": "Retour à la maison", "cinema_aller": "Route vers la Cité internationale",
                 "cinema_retour": "Retour en Kangoo", "midi_dimanche": "Retour à la maison", "monts_aller": "Route vers les monts d'Or",
                 "monts_retour": "Retour des monts d'Or"}[nom]
        for k, (dist, den) in enumerate(D):
            st = {"action": t["textes"][k], "piece": KANGOO, "lieu": TRAJET, "posture": "assis", "charge": "conduite", "mode": "eveille",
                  "parcours": [{"moyen": "voiture", "distance_m": dist, "denivele_m": den}], "titre": titre, "routine": self.routine}
            if t["pensees"][k]:
                st["pensee"] = t["pensees"][k]
            if t["ev"][k]:
                st["ev"] = list(t["ev"][k])
            if k == 0:
                if depart == "garage":
                    st["objets"] = [["obj-kangoo", "en route"], ["obj-cles-kangoo", "contact de la Kangoo"]]
                    st["app"] = {"eteint": ["lumiere-garage"]}
                elif depart == "cour":
                    st["sortie"] = "cour-epicerie"
                    st["objets"] = [list(x) for x in DEPART_BOUTIQUE]
                elif depart == "parking":
                    st["objets"] = [["obj-kangoo", "en route"], ["obj-cles-kangoo", "contact de la Kangoo"]]
            if k == len(D) - 1 and arrivee == "parking":
                st["objets"] = [["obj-kangoo", "parking de la Cité internationale / deuxième sous-sol"], ["obj-cles-kangoo", "poche de la veste"]]
            self.emettre(st)

    # ------------------------------------------------------------ comptoir
    def client_simule(self, s):
        """Thomas Berthier : mêmes répliques, mêmes achats, même paiement que dans sa journée."""
        E = self.ECHANGES
        moment = "matin" if self.i < idx("12:00") else "soir"
        if s.get("achats"):
            especes = "especes" in s.get("argent", {}).get("mouvements", {})
            ventes = [{"produit": a["produit"], "quantite": round(a["quantite"] / self.CAT[a["produit"]]["quantite"]),
                       "paiement": "especes" if especes else "carte"} for a in s["achats"]]
            total = round(sum(v["quantite"] * self.CAT[v["produit"]]["prix"] for v in ventes), 2)
            liste = enumerer([libelle(self.CAT[v["produit"]], v["quantite"]) for v in ventes])
            au_revoir = E["au_revoir_commercant"].get(self.jour, E["au_revoir_commercant"]["defaut"])
            self.faits.append(f"L'horloger est passé ({euros(total)})")
            self.decisions.append(f"{hm(self.i)} : sert Thomas Berthier ({liste}, {euros(total)}, {'espèces' if especes else 'carte'}).")
            return {"texte": f"L'horloger pose sur le comptoir {liste}. « Ça fera {euros(total)}. » Il paie {'en espèces' if especes else 'par carte'}. "
                             f"« {E['au_revoir_client'][moment]} » — « {au_revoir} »", "ventes": ventes,
                    "pensee": choix(self.P["client_connu"]["paiement"], self.date, self.i)}
        accueil = E["accueil_commercant"].get(self.jour, E["accueil_commercant"]["defaut"])
        reponse = E["reponse_client"].get(self.jour, E["reponse_client"]["defaut"])
        conseil = E.get("conseil", {}).get(self.jour)
        texte = f"L'horloger de la rue d'Austerlitz pousse la porte. « {E['salut_client'][moment]} » Robert lève la tête de sa caisse : « {accueil} » — « {reponse} »"
        pensee = choix(self.P["client_connu"]["entree"], self.date, self.i)
        if conseil:
            texte += f" Robert ajoute : « {conseil['commercant']} » — « {conseil['client']} »"
            pensee = conseil["pensee_commercant"]
            self.decisions.append(f"{hm(self.i)} : conseille « {conseil['film']} » à l'horloger.")
        return {"texte": texte + " Il le laisse choisir dans les rayons.", "ev": ["client_habitue"],
                "social": self.fiche["besoins"]["social"]["satisfaction"]["habitue"], "pensee": pensee}

    def note_comptoir(self, fin):
        """Ce que Robert fait au comptoir en plus de servir : café, besoins, journal, voisin, radio, étal."""
        K, S, P = self.R["comptoir"], self.R["seuils"], self.P["comptoir"]
        h, b = self.i, self.sim.besoins
        fait = self.faits_comptoir
        if hm(h) in K["cafes"]:
            n = {"action": P["cafe_toilettes"] if b["toilettes"] < S["toilettes_avant_cafe"] else P["cafe"],
                 "via": (["wc-boutique", "arriere-boutique"] if b["toilettes"] < S["toilettes_avant_cafe"] else ["arriere-boutique"]),
                 "effets": {"cafe": True, "soif": 15} | ({"toilettes": "vide"} if b["toilettes"] < S["toilettes_avant_cafe"] else {}),
                 "consommation": [{"produit": "cafe_boutique", "quantite": 7}], "app": {"allume": ["cafetiere-boutique"], "eteint": ["cafetiere-boutique"]},
                 "ev": ["plaisir_simple"]}
            if self.sim.positions.get("obj-tasse-boutique") == "arriere-boutique / évier":
                n["objets"] = [["obj-tasse-boutique", "boutique / comptoir"]]
            return n
        if h + 1 < fin and b["toilettes"] < S["toilettes_au_comptoir"]:
            return {"action": P["toilettes"], "via": ["wc-boutique"], "effets": {"toilettes": "vide"}}
        if h + 1 < fin and (b["soif"] < S["soif"] or hm(h) in K["verres_d_eau"]):
            return {"action": P["eau"], "via": ["arriere-boutique"], "effets": {"soif": 25}}
        if self.jour in self.C["livraisons"]["grossiste"]["jours"] and hm(h) in K["reassort_apres_livraison"]:
            return {"action": P["reassort"][K["reassort_apres_livraison"].index(hm(h))], "via": ["reserve"]}
        if hm(h) == K["etal_rempli"]:
            return {"action": P["etal_rempli"], "via": ["reserve"]}
        if hm(h) in K["etal_resserre"]:
            return {"action": P["etal_resserre"][K["etal_resserre"].index(hm(h))]}
        G = K["grosses_tetes"]
        if self.jour in G["jours"] and hm(h) == G["debut"]:
            return {"action": self.P["grosses_tetes"]["debut"], "ev": ["plaisir_simple"]}
        return None

    def note_creux(self):
        """Au premier pas sans client après l'heure prévue : journal, voisin, rire."""
        K = self.R["comptoir"]
        h, fait = self.i, self.faits_comptoir
        for k, t in enumerate(K["lectures_du_journal"]):
            if h >= idx(t) and ("journal", k) not in fait and (k + 1 == len(K["lectures_du_journal"]) or h < idx(K["lectures_du_journal"][k + 1])):
                fait.add(("journal", k))
                textes = self.P["journal"].get(self.date) or self.P["journal"]["pensees"]
                return {"action": textes[min(k, len(textes) - 1)], "ev": ["lecture_journal"]}
        G = K["garnier"]
        if self.jour in G["jours"] and h >= idx(G["apres"]) and "garnier" not in fait:
            fait.add("garnier")
            g = choix(self.P["garnier"], self.date, "garnier")
            return {"action": g["texte"], "pensee": g["pensee"], "via": ["trottoir"], "ev": ["bavardage_voisin"], "effets": {"social": 2}}
        GT = K["grosses_tetes"]
        if self.jour in GT["jours"] and h >= idx(GT["rire_apres"]) and "rire" not in fait:
            fait.add("rire")
            return {"action": choix(self.P["grosses_tetes"]["rire"], self.date, "rire"), "ev": ["rire"]}
        return None

    def service(self, fin, titre="Boutique ouverte"):
        k_vide = 0
        vides = self.P["vide"]["dimanche" if self.jour == "dimanche" else ("matin" if self.i < idx("12:00") else "apres")]
        while self.i < fin:
            h = self.i
            client = self.client_simule(self.visites[h]) if h in self.visites else None
            note = self.note_comptoir(fin) or {}
            stock = dict(self.sim.boutique)
            for v in (client or {}).get("ventes", []):
                stock[v["produit"]] -= v["quantite"]
                if stock[v["produit"]] < 0:
                    raise Incoherence(f"{hm(h)} : le magasin n'a plus assez de {v['produit']} pour l'horloger")
            self.comptoir.stock = stock
            r = self.comptoir.pas(h)
            if not r["texte"] and not client and not note:
                note = self.note_creux() or {}
            texte = r["texte"]
            ev = list(r["ev"])
            effets = dict(r.get("effets", {}))
            ventes = list(r["ventes"])
            nb = r["clients"]
            pensee = note.pop("pensee", None)
            if client:
                texte = client["texte"] + ((" Puis " + texte[0].lower() + texte[1:]) if texte else "")
                ventes = client.get("ventes", []) + ventes
                nb += 1 if client.get("ventes") else 0
                ev = list(dict.fromkeys(client.get("ev", []) + ev))
                if client.get("social"):
                    effets["social"] = round(effets.get("social", 0) + client["social"], 2)
                pensee = pensee or client.get("pensee")
            action = note.pop("action", None)
            if action and texte:
                txt = action + " " + texte
            elif action or texte:
                txt = action or texte
            else:
                txt = vides[k_vide % len(vides)]
                k_vide += 1
            if any(t["paiement"] == "ardoise" for t in self.comptoir_dernier(r)):
                txt += " " + self.P["comptoir"]["ardoise"]
            for e, v in note.pop("effets", {}).items():
                effets[e] = v if (v == "vide" or isinstance(v, bool)) else round(effets.get(e, 0) + v, 2)
            if not pensee:
                pensee = self.pensee_habitue(r)
            st = {"action": txt, "pensee": pensee, "piece": "boutique", "lieu": BOUTIQUE, "mode": "travail", "charge": "service", "posture": "debout",
                  "radio": True, "ev": list(dict.fromkeys(note.pop("ev", []) + ev)), "titre": titre, "routine": self.routine}
            if ventes:
                st["ventes"] = ventes
            if nb:
                st["clients"] = nb
            if effets:
                st["effets"] = effets
            if r.get("ruptures"):
                st["ruptures"] = r["ruptures"]
                self.decisions.append(f"{hm(h)} : rupture : {', '.join(r['ruptures'])}.")
            if r.get("argent"):
                st["argent"] = r["argent"]
            st.update(note)
            if not st.get("pensee"):
                self.preoccupation(st)
            self.emettre(st, bloc="service")

    @staticmethod
    def comptoir_dernier(r):
        return r.get("details", [])

    def pensee_habitue(self, r):
        for t in r.get("details", []):
            if t["habitue"] and t["qui"] in self.P["habitues"]:
                return choix(self.P["habitues"][t["qui"]], self.date, t["qui"])
        return None

    # ------------------------------------------------------------ soirées
    def tele(self, fin, textes, avec_josiane_jusqua=None):
        """Télévision jusqu'à fin, ou jusqu'à ce que la fatigue l'emporte."""
        S = self.R["seuils"]
        k = 0
        while self.i < fin:
            if self.sim.besoins["energie"] < S["fatigue_coucher"]:
                self.decisions.append(f"{hm(self.i)} : épuisé (énergie {round(self.sim.besoins['energie'], 1)}), il éteint la télévision et monte se coucher.")
                self.emettre({"action": self.P["tele"]["fatigue"], "pensee": "Au lit.", "piece": "sejour", "posture": "assis", "charge": "repos", "mode": "eveille",
                              "app": {"eteint": ["television"]}, "effets": {"social": 1.0}, "objets": [["obj-telecommande", "sejour / accoudoir du fauteuil"]],
                              "titre": "Télévision", "routine": "rt-soir"})
                return
            if self.sim.besoins["toilettes"] < S["toilettes"]:
                self.emettre({"action": "Passe aux toilettes pendant une publicité.", "piece": "wc", "posture": "debout", "effets": {"toilettes": "vide"},
                              "titre": "Télévision", "routine": "rt-soir"})
                continue
            avec = avec_josiane_jusqua is None or self.i < avec_josiane_jusqua
            t = textes[k] if k < len(textes) else choix(textes[-3:], self.date, self.i)
            if avec_josiane_jusqua is not None and self.i == avec_josiane_jusqua:
                t = self.P["tele"]["josiane_monte"]
            st = {"action": t, "piece": "sejour", "posture": "assis", "charge": "repos", "mode": "loisir", "tele": True, "titre": "Télévision", "routine": "rt-soir"}
            if avec:
                st["effets"] = {"social": 1.0}
            if k == 1:
                st["ev"] = ["rire"]
            if k == 6:
                st["pensee"] = choix(self.P["tele"]["pensees"], self.date, self.i)
            self.emettre(st)
            k += 1
        self.emettre({"action": self.P["tele"]["fin"], "piece": "sejour", "posture": "assis", "charge": "repos", "mode": "eveille", "app": {"eteint": ["television"]},
                      "objets": [["obj-telecommande", "sejour / accoudoir du fauteuil"]], "titre": "Télévision", "routine": "rt-soir"})

    def coucher(self, scene="toilette_soir"):
        """Toilette du soir, extinction, endormissement selon l'état, puis sommeil jusqu'à minuit."""
        self.jouer(scene, variante="defaut")
        exc = self.sim.emo["excitation"]
        e = self.emettre({"action": "Éteint la lampe de chevet.", "piece": "chambre", "posture": "allongé", "charge": "repos", "app": {"eteint": ["lumiere-chambre"]},
                          "ev": ["souvenir_excitant"] if exc > 0.45 else [], "titre": "Endormissement", "routine": "rt-soir"})
        self.j.extinction = e["heure"]
        latence = self.sim.latence_endormissement(e["emotions"])
        self.j.endormissement = latence
        if latence > self.fiche["sante"]["sommeil"]["endormissement_minutes_normal"]:
            self.decisions.append(f"{e['heure']} : endormissement en {latence} minutes (excitation {e['emotions']['excitation']}, anxiété {e['emotions']['anxiete']}).")
        textes = self.P["endormissement"]["agite" if latence > 15 else "calme"]
        n = latence // 5 - 1
        for k in range(n):
            dernier = k == n - 1
            self.emettre({"action": self.P["endormissement"]["endormi"] if dernier else textes[k % len(textes)], "piece": "chambre", "posture": "allongé",
                          "charge": "sommeil" if dernier else "repos", "titre": "Endormissement", "routine": "rt-soir"})
        debut = self.i
        while self.i < PAS_PAR_JOUR:
            self.emettre({"action": "Dort.", "piece": "chambre", "mode": "sommeil", "charge": "sommeil", "posture": "allongé",
                          "phase_sommeil": phase_sommeil((self.i - debut) * 5), "titre": "Sommeil", "routine": "sommeil"}, bloc="sommeil")
        self.mem["endormi_a"] = debut - PAS_PAR_JOUR

    def soiree_semaine(self):
        plat = self.MENUS[self.jour]["diner"]["plat"]
        self.jouer("soiree", fmt={"plat": plat})
        fin = idx(self.R["fin_tele"].get(self.jour, self.R["fin_tele"]["defaut"]))
        self.tele(fin, self.P["tele"]["defaut"], avec_josiane_jusqua=fin - 5)
        self.coucher()

    def soiree_match(self, match):
        self.jouer("soiree_match")
        moments = {m["heure"]: m for m in match["moments"]}
        reactions = {"but_adverse": " Robert tape du poing sur l'accoudoir.",
                     "but_equipe": " Robert se lève d'un bond en criant, puis se plaque la main sur la bouche : Josiane dort au-dessus.",
                     "qualification_equipe": " Robert reste debout devant l'écran, les bras levés, sans un bruit."}
        fin = idx(next(m["heure"] for m in match["moments"] if m.get("fin"))) + 1
        en_pause, mi_temps = False, None
        k = 0
        while self.i < fin:
            h = hm(self.i)
            m = moments.get(h)
            avec = mi_temps is None or self.i <= mi_temps
            st = {"piece": "sejour", "posture": "assis", "charge": "repos", "mode": "loisir", "tele": "match", "titre": match["nom"].split(",")[0], "routine": "rt-soir"}
            if avec:
                st["effets"] = {"social": 1.0}
            if m:
                en_pause = bool(m.get("pause"))
                if en_pause:
                    mi_temps = self.i
                st["action"] = m["texte"] + reactions.get(m.get("ev"), "")
                if m.get("ev"):
                    st["ev"] = [m["ev"]]
                if m.get("fin"):
                    self.faits.append("Lyon qualifié au Bernabéu (1-1)")
            elif en_pause and mi_temps is not None and self.i == mi_temps + 1:
                b = self.sim.besoins
                st.update({"action": "Mi-temps. Josiane monte se coucher. Il passe aux toilettes et se sert un verre d'eau.", "via": ["wc", "cuisine"],
                           "effets": {"toilettes": "vide", "soif": 20}, "posture": "debout", "mode": "eveille"})
            elif en_pause:
                st["action"] = "La mi-temps ; les consultants refont la première période."
            else:
                st["action"] = "Suit le match, penché en avant, les coudes sur les genoux." if k % 3 else "Suit le match ; Lyon subit."
                st["ev"] = ["match_tension"]
            self.emettre(st)
            k += 1
        self.jouer("apres_match")
        self.coucher("toilette_soir_match")

    def soiree_samedi(self):
        self.jouer("soiree_samedi")
        Bl = self.B["belote"]["defaut"]
        self.emettre(copy.deepcopy(Bl["arrivee"]))
        P = self.P["belote"]
        k, gagnees, perdues = 0, 0, 0
        while self.i < idx("23:00"):
            st = copy.deepcopy(Bl["partie"])
            if k % 6 == 5:
                gagne = tirage(self.date, self.i, "belote") < 0.45
                st["action"] = P["gagnee" if gagne else "perdue"]
                st["ev"] = ["belote_gagnee" if gagne else "belote_perdue"]
                gagnees += gagne
                perdues += not gagne
            else:
                st["action"] = P["parties"][k % len(P["parties"])]
                if k % 6 == 2:
                    st["pensee"] = choix(P["pensees"], self.date, self.i)
                if "rit" in st["action"]:
                    st["ev"] = ["rire"]
            if self.sim.besoins["toilettes"] < self.R["seuils"]["toilettes"]:
                st.update({"action": "Passe aux toilettes entre deux donnes.", "piece": "wc", "posture": "debout", "effets": {"toilettes": "vide"}})
            self.emettre(st)
            k += 1
        self.emettre(copy.deepcopy(Bl["depart"]))
        self.faits.append(f"Belote avec les Morel : {gagnees} partie{'s' if gagnees > 1 else ''} gagnée{'s' if gagnees > 1 else ''}, "
                          f"{perdues} perdue{'s' if perdues > 1 else ''}")
        self.coucher()

    # ------------------------------------------------------------ journées
    def matin_commerce(self):
        self.routine = {"mercredi": "rt-mercredi", "samedi": "rt-samedi", "dimanche": "rt-dimanche"}.get(self.jour, "rt-commerce")
        self.nuit(idx(self.R["reveil"]["commerce"]))
        for nom in ("reveil", "toilette", "petit_dejeuner", "depart_matin"):
            self.jouer(nom)
        self.route("aube", "aube", depart="garage")
        self.jouer("arrivee_boutique")
        self.jouer("pain")
        self.jouer("grossiste" if self.jour in self.C["livraisons"]["grossiste"]["jours"] else "mise_en_rayon")
        self.jouer("ouverture")

    def journee_commerce(self):
        plages = [(idx(a), idx(b)) for a, b in self.C["horaires"][self.jour]]
        self.matin_commerce()
        o1, f1 = plages[0]
        if self.i != o1:
            raise Incoherence(f"ouverture prévue à {hm(o1)}, l'agent en est à {hm(self.i)}")
        self.service(f1)
        if self.jour == "dimanche":
            return self.apres_midi_dimanche()
        self.jouer("fermeture_midi")
        self.route("midi", "midi", depart="cour")
        self.jouer("dejeuner")
        self.jouer("sieste")
        self.jouer("depart_apres_midi")
        self.route("apres_midi", "apres_midi", depart="garage")
        self.jouer("reouverture")
        o2, f2 = plages[1]
        if self.i != o2:
            raise Incoherence(f"réouverture prévue à {hm(o2)}, l'agent en est à {hm(self.i)}")
        self.service(f2)
        sc = self.scene("fermeture_soir")
        for spec in sc[:2]:
            self.emettre(self.appliquer_role(spec))
        if self.jour in self.R["commande_grossiste"]:
            self.jouer("commande_jeudi", variante="defaut")
        self.emettre(self.appliquer_role(sc[2]))
        self.route("soir", "soir", depart="cour")
        match = self.MONDE_EV["match-real-lyon"]
        if self.date == match["date"]:
            self.soiree_match(match)
        elif self.jour == "samedi":
            self.soiree_samedi()
        else:
            self.soiree_semaine()

    def apres_midi_dimanche(self):
        # fermeture : caisse, puis la fin de semaine (tri, ménage, comptes, bon de commande de mardi), puis le cabas
        sc = self.scene("fermeture_dimanche", variante="defaut")
        for spec in sc[:2]:
            self.emettre(self.appliquer_role(spec))
        self.jouer("fin_de_semaine", variante="defaut")
        self.faits.append("Fin de semaine à la boutique : produits périmés triés, ménage")
        for spec in sc[2:]:
            self.emettre(self.appliquer_role(spec))
        self.route("midi_dimanche", "midi_dimanche", depart="cour")
        self.jouer("dejeuner_dimanche", variante="defaut")
        self.jouer("sieste_dimanche", variante="defaut")
        self.jouer("vote", variante="defaut")
        self.faits.append("A voté au premier tour des régionales, avec Josiane")
        self.jouer("preparation_randonnee", variante="defaut")
        self.route("monts_aller", "monts_aller", depart="garage")
        self.jouer("randonnee", variante="defaut")
        self.route("monts_retour", "monts_retour", depart="parking")
        self.jouer("retour_randonnee", variante="defaut")
        self.faits.append("Randonnée dans les monts d'Or avec Josiane : mont Thou et mont Cindre, 8 km")
        self.jouer("fin_dimanche", variante="defaut")
        self.jouer("diner_dimanche", variante="defaut")
        fin = idx(self.R["fin_tele"]["dimanche"])
        self.tele(fin, self.P["tele"]["dimanche"], avec_josiane_jusqua=fin - 5)
        self.coucher()

    def journee_lundi(self):
        self.routine = "rt-lundi"
        self.nuit(idx(self.R["reveil"]["lundi"]))
        self.jouer("lundi")
        self.route("lundi_matin", "lundi_matin", depart="garage")
        self.jouer("lundi_banque")
        self.route("lundi_midi", "lundi_midi", depart="cour")
        self.jouer("lundi_matinee")
        self.jouer("lundi_apres_midi")
        self.faits.append("Potager : deux rangs retournés, radis semés")
        self.route("cinema_aller", "cinema_aller", depart="garage", arrivee="parking")
        self.jouer("lundi_cinema")
        self.faits.append("Cinéma avec Josiane : « The Ghost Writer »")
        self.route("cinema_retour", "cinema_retour", depart="parking")
        self.jouer("lundi_coucher")
        exc = self.sim.emo["excitation"]
        e = self.emettre({"action": "Éteint la lampe de chevet.", "piece": "chambre", "posture": "allongé", "charge": "repos", "app": {"eteint": ["lumiere-chambre"]},
                          "titre": "Endormissement", "routine": "rt-soir"})
        self.j.extinction = e["heure"]
        latence = self.sim.latence_endormissement(e["emotions"])
        self.j.endormissement = latence
        n = latence // 5 - 1
        for k in range(n):
            dernier = k == n - 1
            self.emettre({"action": "S'endort." if dernier else "Repense au film, à la maison de verre sous la pluie.", "piece": "chambre", "posture": "allongé",
                          "charge": "sommeil" if dernier else "repos", "titre": "Endormissement", "routine": "rt-soir"})
        debut = self.i
        while self.i < PAS_PAR_JOUR:
            self.emettre({"action": "Dort.", "piece": "chambre", "mode": "sommeil", "charge": "sommeil", "posture": "allongé",
                          "phase_sommeil": phase_sommeil((self.i - debut) * 5), "titre": "Sommeil", "routine": "sommeil"}, bloc="sommeil")
        self.mem["endormi_a"] = debut - PAS_PAR_JOUR

    def vivre(self):
        if self.C["horaires"][self.jour]:
            self.journee_commerce()
        else:
            self.journee_lundi()
        return self.terminer()

    def terminer(self):
        if self.i != PAS_PAR_JOUR:
            raise Incoherence(f"la journée de l'agent compte {self.i} pas")
        etat_final, stats = self.sim.terminer(self.j.extinction, self.j.endormissement)
        self.mem.pop("evocations_du_jour", None)
        self.mem["ardoises"] = self.comptoir.ardoises
        if self.recette:
            self.mem.setdefault("recettes", {})[self.date] = self.recette
        etat_final["agent"] = self.mem
        self.j.ecarts = self.decisions or ["Aucun écart notable."]
        self.j.bilan = [f"**{f}**" for f in self.faits] or ["Journée sans fait marquant."]
        for s in self.j.segments:
            s.pop("_bloc", None)
        return self.sim.steps, etat_final, stats
