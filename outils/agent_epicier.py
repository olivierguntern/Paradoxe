"""Agent autonome d'un commerçant : Robert Chazal, l'épicier de la Grande-Rue.

La journée suit les horaires de la boutique (fiche, section commerce) : lever,
livraisons, service des clients, pauses, fermeture, soirée. Chaque pas est
décidé selon l'état lu dans la simulation (besoins, émotions, objets, caisse).

Les clients anonymes ne sont pas simulés : leur nombre à chaque pas est tiré
de façon déterministe autour de l'affluence moyenne de l'heure, et chacun
laisse un panier moyen dans la caisse. Thomas Berthier, lui, est simulé : aux
pas où sa journée le fait entrer dans la boutique, Robert le sert, avec les
mêmes répliques (data/monde/echanges.json) et les mêmes achats.
"""
import copy
import datetime
import json
import os

from agent import JOURS, MOIS, choix, phase_sommeil, tirage
from moteur import PAS_PAR_JOUR, Incoherence, Journee, Simulation, hm, idx


def euros(v):
    return f"{v:.2f}".replace(".", ",") + " €"


class AgentEpicier:
    def __init__(self, fiche, dossier, date, etat):
        self.fiche = fiche
        self.R = json.load(open(os.path.join(dossier, "regles.json")))
        self.PENSEES = json.load(open(os.path.join(dossier, "pensees.json")))
        racine = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(dossier))))
        self.racine = racine
        self.COMMERCE = fiche["commerce"]
        self.ECHANGES = json.load(open(os.path.join(racine, "data", "monde", "echanges.json")))[self.COMMERCE["id"]]
        self.MONDE_EV = json.load(open(os.path.join(racine, "data", "monde", "evenements.json")))
        self.date = date
        d = datetime.date.fromisoformat(date)
        self.jour = JOURS[d.weekday()]
        self.date_txt = f"{d.day} {MOIS[d.month - 1]}"
        self.sim = Simulation(fiche, date, etat)
        self.mem = copy.deepcopy(etat.get("agent")) or {"endormi_a": idx(self.R["endormi_la_veille_du_premier_jour"]) - PAS_PAR_JOUR,
                                                        "evocations": {}}
        self.mem["jour_index"] = self.mem.get("jour_index", -1) + 1
        self.evocations_du_jour = {}
        self.j = Journee(date, self.jour, extinction="22:30")
        self.j.methode = [
            "Généré par l'agent autonome du commerçant (outils/agent_epicier.py) à partir de ses règles (data/agents/robert-chazal/).",
            "Clients anonymes tirés de façon déterministe selon l'affluence de l'heure ; visites de Thomas Berthier lues dans sa propre journée.",
            "Calculé par outils/moteur.py avec les règles de la fiche : déplacements, lumière, besoins, émotions, caisse.",
            "La journée part de l'état exact de la fin de la veille.",
        ]
        self.faits, self.decisions = [], []
        self.recette, self.clients, self.vides = 0.0, 0, 0
        self.visites = self.lire_visites()

    # ------------------------------------------------------------ outils
    @property
    def i(self):
        return len(self.sim.steps)

    def ouverture(self):
        return [(idx(a), idx(b)) for a, b in self.COMMERCE["horaires"][self.jour]]

    def lire_visites(self):
        """Pas où le client simulé est dans la boutique, avec ses achats et son paiement."""
        chemin = os.path.join(self.racine, "data", "timelines", self.R["client"], f"{self.date}.json")
        if not os.path.exists(chemin):
            return {}
        J = json.load(open(chemin))
        out = {}
        for s in J["pas"]:
            if s.get("lieu") == self.COMMERCE["id"]:
                out[s["pas"]] = s
        return out

    def emettre(self, pas, titre, routine, bloc=None):
        st = copy.deepcopy(pas)
        s = {"titre": titre, "routine": routine, "piece": st.pop("piece", self.sim.piece), "lieu": st.pop("lieu", "domicile"),
             "mode": st.pop("mode", "eveille"), "charge": st.pop("charge", "simple"), "posture": st.pop("posture", "debout")}
        st.setdefault("pensee", None)
        entree = self.sim.pas(st, s)
        segs = self.j.segments
        cle = bloc or titre
        if segs and segs[-1]["titre"] == titre and segs[-1].get("_bloc") == cle:
            segs[-1]["pas"].append(st)
        else:
            segs.append({"debut": hm(entree["pas"]), "titre": titre, "routine": routine, "pas": [st], "_bloc": cle})
        return entree

    def conso(self, repas):
        return [{"produit": p, "quantite": q} for p, q in self.R["consommations"][repas]]

    def preoccupation(self, p):
        """Ajoute parfois une pensée liée à la préoccupation la plus pesante."""
        if p.get("pensee") or tirage(self.date, self.i, "preoc") >= self.PENSEES["frequence_preoccupations"]:
            return p
        prs = {x["id"]: x for x in self.fiche["vie_interieure"]["preoccupations_semaine"]}
        meilleur, score = None, -1
        for pid, spec in self.PENSEES["preoccupations"].items():
            if spec.get("jusqua") and self.date > spec["jusqua"]:
                continue
            if self.evocations_du_jour.get(pid, 0) >= 2:
                continue
            depuis = self.mem["jour_index"] * PAS_PAR_JOUR + self.i - self.mem["evocations"].get(pid, -10 ** 6)
            sc = prs[pid]["intensite_initiale"] * (1 + min(depuis, 2000) / 60)
            if sc > score:
                meilleur, score = pid, sc
        if meilleur:
            spec = self.PENSEES["preoccupations"][meilleur]
            p["pensee"] = choix(spec["textes"], self.date, self.i, meilleur)
            p.setdefault("ev", []).append(spec["evenement"])
            self.mem["evocations"][meilleur] = self.mem["jour_index"] * PAS_PAR_JOUR + self.i
            self.evocations_du_jour[meilleur] = self.evocations_du_jour.get(meilleur, 0) + 1
        return p

    def besoin_pressant(self, titre, routine):
        """Toilettes ou soif sous le seuil : un pas pour y répondre, dans l'étage où il se trouve."""
        S = self.R["seuils"]
        bas = self.fiche["domicile"]["pieces"]
        niveau = {pc["id"]: pc.get("niveau", 0) for pc in bas}.get(self.sim.piece, 0)
        if self.sim.besoins["toilettes"] < S["toilettes"]:
            if niveau == 0 and self.sim.piece == "boutique":
                p = {"action": "Passe aux toilettes du fond, au retour d'un client.", "piece": "boutique", "via": ["wc-boutique"]}
            else:
                p = {"action": "Passe aux toilettes.", "piece": "wc-boutique" if niveau == 0 else "wc"}
            p.update({"effets": {"toilettes": "vide"}, "charge": "simple", "posture": "debout"})
        elif self.sim.besoins["soif"] < S["soif"]:
            if self.sim.piece == "boutique":
                p = {"action": "Boit un grand verre d'eau à l'évier de l'arrière-boutique.", "piece": "boutique", "via": ["arriere-boutique"]}
            else:
                p = {"action": "Boit un grand verre d'eau.", "piece": self.sim.piece}
            p.update({"effets": {"soif": 25}, "charge": "simple", "posture": "debout"})
        else:
            return False
        self.emettre(p, titre, routine, bloc="besoin")
        return True

    # ------------------------------------------------------------ nuit et matin
    def nuit(self, reveil_i):
        titre = f"Nuit de {JOURS[(JOURS.index(self.jour) - 1) % 7]} à {self.jour}"
        debut = self.mem["endormi_a"]
        n_reve = 0
        ancienne = None
        while self.i < reveil_i:
            m = (self.i - debut) * 5
            phase = phase_sommeil(m)
            p = {"action": "Dort." if phase != "micro-éveil" else "Se retourne en grognant, se rendort.", "piece": "chambre", "mode": "sommeil",
                 "charge": "sommeil", "posture": "allongé", "phase_sommeil": phase}
            if phase == "paradoxal" and ancienne != "paradoxal" and n_reve < 3:
                r = choix(self.PENSEES["reves"], self.date, self.i)
                p["reve"], p["ev"] = r["texte"], [r["ev"]]
                n_reve += 1
            self.emettre(p, titre, "sommeil", bloc="nuit")
            ancienne = phase

    def lever(self, naturel):
        T, R = "Lever", "rt-matin"
        pos = self.sim.positions
        lampe = {"allume": ["lumiere-chambre"]} if self.i < self.sim.LEVER else {}
        self.emettre({"action": ("Se réveille de lui-même, sans réveil." if naturel else "La sonnerie du réveil. Il l'arrête d'un geste et s'assoit au bord du lit en soufflant.") +
                                " Attache à son poignet la montre de Josiane.",
                      "piece": "chambre", "posture": "assis", "charge": "repos", "ev": [] if naturel else ["reveil_sonnerie"], "app": lampe,
                      "objets": [{"objet": "obj-montre", "de": pos["obj-montre"], "vers": "poignet gauche"},
                                 {"objet": "obj-lunettes", "de": pos["obj-lunettes"], "vers": "sur son front"}]}, T, R)
        self.emettre({"action": "Passe aux toilettes.", "piece": "wc", "effets": {"toilettes": "vide"}}, T, R)
        self.emettre({"action": "Met la cafetière en route, allume la radio, beurre deux tartines.", "piece": "cuisine", "charge": "cuisine",
                      "posture": "debout", "app": {"allume": ["radio-cuisine"]}, "radio": True}, "Petit-déjeuner", R)
        self.emettre({"action": "Déjeune debout contre le buffet en écoutant les nouvelles.", "piece": "cuisine", "charge": "repos", "posture": "debout",
                      "consommation": self.conso("petit_dejeuner"), "effets": {"faim": 40, "soif": 15, "cafe": 1}, "ev": ["plaisir_simple"],
                      "radio": True}, "Petit-déjeuner", R)
        self.emettre({"action": "Avale son comprimé pour la tension avec un verre d'eau, rince le bol, éteint la radio.", "piece": "cuisine",
                      "charge": "simple", "posture": "debout", "effets": {"soif": 20}, "app": {"eteint": ["radio-cuisine"]}}, "Petit-déjeuner", R)
        self.emettre({"action": "Douche rapide.", "piece": "salle-de-bain", "charge": "simple", "effets": {"hygiene": 75}}, "Toilette", R)
        self.emettre({"action": "Se rase" + (" et taille sa moustache." if self.jour == "dimanche" else ".") , "piece": "salle-de-bain",
                      "charge": "precision"}, "Toilette", R)
        self.emettre({"action": "S'habille : chemise à carreaux, pantalon de velours.", "piece": "chambre", "charge": "simple"}, "Toilette", R)

    def descendre(self, texte, titre, routine):
        pos = self.sim.positions
        objets = [] if pos["obj-cles"] == "poche du pantalon" else [{"objet": "obj-cles", "de": pos["obj-cles"], "vers": "poche du pantalon"}]
        if pos["obj-blouse"] != "porté":
            objets.append({"objet": "obj-blouse", "de": pos["obj-blouse"], "vers": "porté"})
        self.emettre({"action": texte, "piece": "arriere-boutique", "charge": "simple", "escalier": {"sens": "descente"}, "objets": objets,
                      "ev": ["effort_physique"]}, titre, routine)

    # ------------------------------------------------------------ boutique
    def preparation(self, ouverture_i):
        T, R = "Préparation de la boutique", "rt-boutique"
        pain_i = ouverture_i - self.R["livraison_pain_avant_ouverture_minutes"] // 5
        G = self.R["livraison_grossiste"]
        grossiste = self.jour in G["jours"]
        g_i = idx(G["heure"])
        self.emettre({"action": "Allume la boutique et la réserve, sort les cagettes de fruits sur l'étal.", "piece": "boutique", "charge": "simple",
                      "app": {"allume": ["lumiere-boutique"]}, "via": ["reserve"]}, T, R)
        pain = False
        while self.i < ouverture_i - 1:
            if self.i >= pain_i and not pain and not (grossiste and g_i <= self.i < g_i + G["pas"]):
                pain = True
                self.emettre({"action": "Ouvre la porte au livreur de la boulangerie : deux panières de baguettes. Il en garde une pour lui.",
                              "piece": "boutique", "via": ["trottoir"], "charge": "simple", "production": [{"produit": "pain", "quantite": 1}]},
                             "Livraison du pain", R)
            elif grossiste and g_i <= self.i < g_i + G["pas"]:
                k = self.i - g_i
                textes = ["Le camion du grossiste se gare en double file. Robert signe le bon de livraison.",
                          "Rentre les cagettes de fruits et légumes, puis les packs de lait.",
                          "Porte les cartons d'épicerie dans la réserve.",
                          "Pose la dernière cagette et se tient les reins une minute."]
                p = {"action": textes[min(k, 3)], "piece": "reserve" if k >= 2 else "boutique", "mode": "effort", "charge": "simple",
                     "ev": ["livraison" if k == 0 else "effort_physique"]}
                if k == 0:
                    p["via"] = ["trottoir"]
                if k == G["pas"] - 1:
                    p["ev"] = ["mal_de_dos"]
                    p["pensee"] = choix(self.PENSEES["preoccupations"]["pre-dos"]["textes"], self.date, self.i)
                self.emettre(p, "Livraison du grossiste", R)
                if k == G["pas"] - 1:
                    self.faits.append("Livraison du grossiste")
            else:
                self.emettre({"action": choix(["Met en rayon les produits frais.", "Remplit la vitrine réfrigérée.", "Aligne les boîtes de conserve.",
                                               "Vérifie les dates sur les yaourts."], self.date, self.i), "piece": "boutique", "charge": "simple"},
                             T, R)
        self.emettre({"action": "Lève le rideau de fer, balaie le trottoir devant la vitrine, allume la radio de la boutique.", "piece": "boutique",
                      "via": ["trottoir"], "charge": "simple", "app": {"allume": ["radio-boutique"]}}, T, R)

    def service(self, fin_i, titre="Boutique ouverte"):
        R = "rt-boutique"
        A = self.COMMERCE["affluence_clients_par_pas"]
        reperes = sorted((idx(h), v) for h, v in A.items() if h != "principe")
        cafes = {idx(h) for h in self.R["pauses_cafe"]}
        while self.i < fin_i:
            if self.i in self.visites:
                self.servir_client_connu(self.visites[self.i], titre)
                continue
            if self.i in cafes:
                self.emettre({"action": "Va se servir un café dans l'arrière-boutique et revient au comptoir, la tasse à la main.", "piece": "boutique",
                              "via": ["arriere-boutique"], "charge": "simple", "consommation": self.conso("cafe"), "effets": {"cafe": 1, "soif": 10},
                              "ev": ["plaisir_simple"], "radio": True}, titre, R, bloc="pause")
                continue
            if self.i + 1 < fin_i and self.i not in self.visites and self.besoin_pressant(titre, R):
                continue
            moyenne = next((v for h, v in reversed(reperes) if h <= self.i), 0.5)
            n = int(moyenne + tirage(self.date, self.i, "clients"))
            p = {"piece": "boutique", "mode": "travail", "charge": "service", "posture": "debout", "radio": True}
            if n == 0:
                self.vides += 1
                p["action"] = choix(self.PENSEES["service"]["vide"], self.date, self.i)
                if self.vides == 4:
                    p["ev"] = ["boutique_vide"]
                    self.vides = 0
            else:
                self.vides = 0
                p["action"] = choix(self.PENSEES["service"]["un"], self.date, self.i) if n == 1 else \
                    choix(self.PENSEES["service"]["plusieurs"], self.date, self.i).replace("{n}", str(n))
                montant = round(sum(self.COMMERCE["panier_moyen_eur"] * (0.5 + tirage(self.date, self.i, "panier", k)) for k in range(n)), 1)
                p["argent"] = {"caisse": montant}
                p["effets"] = {"social": self.fiche["besoins"]["social"]["satisfaction"]["client_par_pas"] * min(n, 3)}
                ev = []
                if n >= 3:
                    ev.append("affluence")
                if tirage(self.date, self.i, "presse") < 0.06:
                    ev.append("client_presse")
                elif tirage(self.date, self.i, "habitue") < 0.15:
                    ev.append("client_habitue")
                if ev:
                    p["ev"] = ev
                self.recette += montant
                self.clients += n
            self.emettre(self.preoccupation(p), titre, R, bloc="service")

    def servir_client_connu(self, s, titre):
        """Sert Thomas : mêmes répliques, mêmes achats, même paiement que dans sa journée."""
        R, E = "rt-boutique", self.ECHANGES
        moment = "matin" if self.i < idx("12:00") else "soir"
        if s.get("achats"):
            total = round(-sum(s.get("argent", {}).get("mouvements", {}).values()), 2)
            especes = "especes" in s.get("argent", {}).get("mouvements", {})
            cat = {c["produit"]: c for c in self.COMMERCE["catalogue"]}
            noms = []
            for a in s["achats"]:
                c = cat.get(a["produit"])
                if c and c["vente"] == "à la pièce":
                    noms.append(f"{round(a['quantite'] / c['quantite'])} {c['unite']}")
                else:
                    noms.append(c["nom"] if c else a["nom"])
            liste = noms[0] if len(noms) == 1 else ", ".join(noms[:-1]) + " et " + noms[-1]
            au_revoir = E["au_revoir_commercant"].get(self.jour, E["au_revoir_commercant"]["defaut"])
            p = {"action": f"Encaisse l'horloger : {liste}. « Ça fera {euros(total)}. »" +
                           (" Il paie en espèces." if especes else " Il paie par carte.") +
                           f" « {E['au_revoir_client'][moment]} » « {au_revoir} »",
                 "argent": {"caisse" if especes else "compte": total},
                 "pensee": choix(self.PENSEES["apres_client_connu"], self.date, self.i)}
            self.recette += total
            self.faits.append(f"L'horloger est passé ({euros(total)})")
            self.decisions.append(f"{hm(self.i)} : sert Thomas Berthier ({euros(total)}, {'espèces' if especes else 'carte'}).")
        else:
            accueil = E["accueil_commercant"].get(self.jour, E["accueil_commercant"]["defaut"])
            reponse = E["reponse_client"].get(self.jour, E["reponse_client"]["defaut"])
            p = {"action": f"L'horloger de la rue d'Austerlitz pousse la porte. « {E['salut_client'][moment]} » Robert lève la tête de sa caisse : "
                           f"« {accueil} » « {reponse} » Il le laisse choisir dans les rayons.",
                 "ev": ["client_habitue"], "effets": {"social": self.fiche["besoins"]["social"]["satisfaction"]["habitue"]}}
            self.clients += 1
        p.update({"piece": "boutique", "mode": "travail", "charge": "service", "posture": "debout", "radio": True})
        self.emettre(p, titre, R, bloc="service")

    def fermeture(self, titre, soir):
        R = "rt-boutique"
        self.emettre({"action": "Baisse le rideau de fer, ferme la porte à clé, éteint la radio.", "piece": "boutique", "via": ["trottoir"],
                      "charge": "simple", "app": {"eteint": ["radio-boutique"]}}, titre, R)
        juste = tirage(self.date, self.i, "caisse") < 0.85
        objectif = self.R["objectif_recette_eur"]
        recette = round(self.recette, 2)
        p = {"action": f"Compte la caisse dans l'arrière-boutique : {euros(recette)} depuis l'ouverture, {self.clients} clients." +
                       (" La caisse tombe juste." if juste else " Il manque quarante centimes ; il recompte, puis laisse tomber."),
             "piece": "arriere-boutique", "charge": "precision", "ev": ["caisse_juste"] if juste else []}
        if soir and recette < objectif:
            p["ev"].append("constat_chiffre")
            p["pensee"] = choix(self.PENSEES["preoccupations"]["pre-chiffre"]["textes"], self.date, self.i)
        self.emettre(p, titre, R)
        if soir:
            pos = self.sim.positions
            self.emettre({"action": "Range la recette dans la sacoche du coffre, raccroche sa blouse, éteint la boutique.", "piece": "arriere-boutique",
                          "charge": "simple", "app": {"eteint": ["lumiere-boutique"]},
                          "objets": [{"objet": "obj-blouse", "de": pos["obj-blouse"], "vers": "arriere-boutique / patère"}]}, titre, R)
            self.faits.append(f"Recette : {euros(recette)} ({self.clients} clients)")
            self.recette, self.clients = 0.0, 0

    def reassort(self):
        """Provisions de l'appartement sous leur seuil : il en remonte du magasin."""
        achats, mots = [], []
        for pid, (seuil, q, texte) in self.R["reassort_maison"]["produits"].items():
            if self.sim.stock.get(pid, 0) < seuil:
                achats.append({"produit": pid, "quantite": q, "prix": 0})
                mots.append(texte)
        return achats, mots

    def monter(self, piece, texte, titre, routine, cles=False):
        p = {"action": texte, "piece": piece, "charge": "simple", "escalier": {"sens": "montee"}}
        achats, mots = self.reassort()
        if achats:
            p["achats"] = achats
            p["action"] += " Remonte du magasin " + (mots[0] if len(mots) == 1 else ", ".join(mots[:-1]) + " et " + mots[-1]) + "."
            self.decisions.append(f"{hm(self.i)} : remonte du magasin {', '.join(mots)} pour l'appartement.")
        if cles:
            p["objets"] = [{"objet": "obj-cles", "de": self.sim.positions["obj-cles"], "vers": "couloir / portemanteau"}]
        self.emettre(p, titre, routine)

    # ------------------------------------------------------------ repas, sieste, soirée
    def repas(self, debut, fin, quoi):
        T, R = "Déjeuner" if quoi == "dejeuner" else "Dîner", "rt-repas"
        n = idx(fin) - self.i
        etapes = [{"action": "Réchauffe un plat cuisiné pris au magasin, allume la radio.", "charge": "cuisine", "posture": "debout",
                   "app": {"allume": ["radio-cuisine"]}, "radio": True},
                  {"action": "Mange à la table de la cuisine, face à la chaise vide." if quoi == "diner" else "Mange à la table de la cuisine en écoutant les informations.",
                   "charge": "repos", "posture": "assis", "consommation": self.conso(quoi), "effets": {"faim": 55, "soif": 20},
                   "ev": ["repas_seul", "plaisir_simple"], "radio": True}]
        while len(etapes) < n - 1:
            etapes.append({"action": "Finit son assiette, un morceau de fromage, la radio en fond." if len(etapes) < 4 else "Reste à table, écoute la radio.",
                           "charge": "repos", "posture": "assis", "radio": True})
        etapes.append({"action": ("Boit son café, " if quoi == "dejeuner" else "") + "fait la vaisselle, éteint la radio.", "charge": "simple",
                       "posture": "debout", "app": {"eteint": ["radio-cuisine"]}} | ({"effets": {"cafe": 1}} if quoi == "dejeuner" else {}))
        for k, p in enumerate(etapes[:n]):
            p["piece"] = "cuisine"
            if k > 1:
                self.preoccupation(p)
            self.emettre(p, T, R)

    def sieste(self, fin):
        T, R = "Sieste", "rt-repos"
        self.emettre({"action": "S'installe dans le fauteuil du séjour et ferme les yeux.", "piece": "sejour", "posture": "assis", "charge": "repos"}, T, R)
        while self.i < idx(fin) - 1:
            self.emettre({"action": "Somnole dans le fauteuil.", "piece": "sejour", "mode": "sieste", "posture": "assis", "charge": "sommeil"}, T, R)
        self.emettre({"action": "Se réveille, s'étire, regarde la photo de Josiane sur le buffet.", "piece": "sejour", "posture": "debout",
                      "charge": "repos", "ev": ["souvenir_josiane"]}, T, R)

    def apres_midi_boutique(self, fin):
        T, R = "Arrière-boutique", "rt-boutique"
        textes = ["Range la réserve après la livraison.", "Écrit les étiquettes de prix à la main.", "Recopie les ventes du matin dans le cahier des comptes.",
                  "Vérifie les dates des produits frais.", "Prépare les cagettes vides pour le grossiste.", "Fait le point du carnet des ardoises."]
        while self.i < fin:
            if self.besoin_pressant(T, R):
                continue
            p = {"action": choix(textes, self.date, self.i), "piece": "arriere-boutique" if self.i % 3 else "reserve", "mode": "travail",
                 "charge": "simple", "posture": "debout"}
            self.emettre(self.preoccupation(p), T, R)

    def television(self, fin, match=None):
        T, R = "Télévision", "rt-soir"
        pos = self.sim.positions
        self.emettre({"action": "S'installe dans le fauteuil du séjour et allume la télévision.", "piece": "sejour", "posture": "assis", "charge": "repos",
                      "mode": "loisir", "app": {"allume": ["television"]}, "tele": True}, T, R)
        moments = {idx(m["heure"]): m for m in (match or {}).get("moments", [])}
        en_match, pause = False, False
        while self.i < fin - 1:
            m = moments.get(self.i)
            # pendant le match, il attend la mi-temps pour se lever
            if not m and (not en_match or pause) and self.i < fin - 4 and self.besoin_pressant(T, R):
                continue
            p = {"piece": "sejour", "posture": "assis", "charge": "repos", "mode": "loisir"}
            if m:
                en_match, pause = not m.get("fin"), bool(m.get("pause"))
                p["action"] = m["texte"] + {"but_adverse": " Robert tape du poing sur l'accoudoir.", "but_equipe": " Robert se lève en criant, seul dans le séjour.",
                                            "qualification_equipe": " Robert reste debout devant l'écran, les bras levés."}.get(m.get("ev"), "")
                if m.get("ev"):
                    p["ev"] = [m["ev"]]
                p["tele"] = "match"
                if m.get("fin"):
                    self.faits.append("Lyon qualifié au Bernabéu (1-1)")
            elif en_match:
                p["action"] = "Mi-temps : se ressert un fond de vin." if pause else "Suit le match, penché en avant."
                p["tele"] = "match"
                if not pause:
                    p["ev"] = ["match_tension"]
            else:
                p["action"] = choix(["Regarde un jeu télévisé.", "Regarde un film sans vraiment le suivre.", "Somnole devant un documentaire.",
                                     "Change de chaîne, revient au film."], self.date, self.i)
                p["tele"] = True
                self.preoccupation(p)
            self.emettre(p, T, R, bloc="tele")
        self.emettre({"action": "Éteint la télévision.", "piece": "sejour", "posture": "debout", "charge": "simple", "app": {"eteint": ["television"]}}, T, R)

    def apres_midi_libre(self, fin):
        T, R = "Après-midi au séjour", "rt-repos"
        self.emettre({"action": "Allume la radio de la cuisine et s'installe au séjour avec ses mots croisés.", "piece": "sejour", "posture": "assis",
                      "charge": "lecture", "mode": "lecture", "app": {"allume": ["radio-cuisine"]}, "via": ["cuisine"]}, T, R)
        cafe = idx("16:30")
        while self.i < fin - 1:
            if self.besoin_pressant(T, R):
                continue
            if self.i == cafe:
                self.emettre({"action": "Se fait un café à la cuisine.", "piece": "cuisine", "charge": "cuisine", "consommation": self.conso("cafe"),
                              "effets": {"cafe": 1, "soif": 10}, "ev": ["plaisir_simple"]}, T, R)
                continue
            p = {"action": choix(["Cherche un mot de sept lettres.", "Fait ses mots croisés, la radio en fond.", "Feuillette un vieux catalogue de fournisseurs.",
                                  "Regarde par la fenêtre la Grande-Rue du dimanche."], self.date, self.i),
                 "piece": "sejour", "posture": "assis", "charge": "lecture", "mode": "lecture", "radio": True}
            self.emettre(self.preoccupation(p), T, R)
        self.emettre({"action": "Éteint la radio.", "piece": "cuisine", "charge": "simple", "app": {"eteint": ["radio-cuisine"]}}, T, R)

    def coucher(self, toilette_i, extinction_i):
        T, R = "Coucher", "rt-soir"
        while self.i < toilette_i:
            self.emettre({"action": "Reste dans le fauteuil, la télévision éteinte.", "piece": "sejour", "posture": "assis", "charge": "repos"}, "Fin de soirée", R)
        self.emettre({"action": "Passe aux toilettes.", "piece": "wc", "effets": {"toilettes": "vide"}}, "Toilette du soir", R)
        while self.i < extinction_i - 1:
            self.emettre({"action": "Se brosse les dents, se lave le visage." if self.i == toilette_i + 1 else "Enfile son pyjama.",
                          "piece": "salle-de-bain" if self.i == toilette_i + 1 else "chambre", "charge": "simple", "effets": {"hygiene": 10}}, "Toilette du soir", R)
        pos = self.sim.positions
        self.emettre({"action": "Pose la montre de Josiane et ses lunettes sur la table de chevet, se couche.", "piece": "chambre", "posture": "allongé",
                      "charge": "repos", "objets": [{"objet": "obj-montre", "de": pos["obj-montre"], "vers": "chambre / table de chevet"},
                                                    {"objet": "obj-lunettes", "de": pos["obj-lunettes"], "vers": "chambre / table de chevet"}]}, T, R)
        e = self.emettre({"action": "Éteint la lumière.", "piece": "chambre", "posture": "allongé", "charge": "repos",
                          "app": {"eteint": ["lumiere-chambre"]}, "ev": ["souvenir_excitant"] if self.sim.emo["excitation"] > 0.45 else []},
                         "Endormissement", R)
        self.j.extinction = e["heure"]
        latence = self.sim.latence_endormissement(e["emotions"])
        self.j.endormissement = latence
        if latence > self.fiche["sante"]["sommeil"]["endormissement_minutes_normal"]:
            self.decisions.append(f"{e['heure']} : endormissement en {latence} minutes (excitation {e['emotions']['excitation']}).")
        for k in range(latence // 5 - 1):
            dernier = k == latence // 5 - 2
            self.emettre({"action": "S'endort." if dernier else "Repense à la soirée, les yeux ouverts.", "piece": "chambre", "posture": "allongé",
                          "charge": "sommeil" if dernier else "repos"}, "Endormissement", R)
        debut = self.i
        while self.i < PAS_PAR_JOUR:
            self.emettre({"action": "Dort.", "piece": "chambre", "mode": "sommeil", "charge": "sommeil", "posture": "allongé",
                          "phase_sommeil": phase_sommeil((self.i - debut) * 5)}, "Sommeil", "sommeil", bloc="sommeil")
        self.mem["endormi_a"] = debut - PAS_PAR_JOUR

    # ------------------------------------------------------------ journées
    def journee_commerce(self):
        plages = self.ouverture()
        dimanche = self.jour == "dimanche"
        cle = "dimanche" if dimanche else "commerce"
        self.nuit(idx(self.R["sonnerie"][cle]))
        self.lever(naturel=False)
        self.descendre("Prend ses clés au portemanteau, descend l'escalier jusqu'à l'arrière-boutique et enfile sa blouse.", "Descente à la boutique", "rt-boutique")
        (o1, f1) = plages[0]
        self.preparation(o1)
        self.service(f1)
        self.fermeture("Fermeture" if dimanche else "Fermeture de midi", soir=dimanche)
        self.monter("cuisine", "Monte à l'appartement" + (" et accroche ses clés au portemanteau." if dimanche else "."), "Pause de midi", "rt-repas",
                    cles=dimanche)
        d, f = self.R["dejeuner"][cle]
        self.repas(d, f, "dejeuner")
        s, sf = self.R["sieste"][cle]
        self.sieste(sf)
        if dimanche:
            self.apres_midi_libre(idx(self.R["diner"]["dimanche"][0]))
        else:
            (o2, f2) = plages[1]
            self.descendre("Redescend à la boutique, renfile sa blouse.", "Retour à la boutique", "rt-boutique")
            self.apres_midi_boutique(o2 - 1)
            self.emettre({"action": "Relève le rideau, rallume la boutique et la radio.", "piece": "boutique", "charge": "simple", "via": ["trottoir"],
                          "app": {"allume": ["lumiere-boutique", "radio-boutique"]}}, "Réouverture", "rt-boutique")
            self.service(f2)
            self.fermeture("Fermeture du soir", soir=True)
            self.monter("cuisine", "Éteint l'arrière-boutique, monte l'escalier et accroche ses clés au portemanteau.", "Fin de journée", "rt-repas", cles=True)
        d, f = self.R["diner"][cle]
        while self.i < idx(d):
            self.emettre({"action": "Range un peu la cuisine.", "piece": "cuisine", "charge": "simple"}, "Fin de journée", "rt-repas")
        self.repas(d, f, "diner")
        match = self.MONDE_EV["match-real-lyon"] if self.date == self.MONDE_EV["match-real-lyon"]["date"] else None
        toilette = idx(self.R["toilette_soir"].get(self.jour, self.R["toilette_soir"]["defaut"]))
        self.television(toilette, match)
        self.coucher(toilette, idx(self.R["extinction"].get(self.jour, self.R["extinction"]["defaut"])))

    def journee_fermeture(self):
        self.nuit(idx(self.R["reveil_naturel_lundi"]))
        self.lever(naturel=True)
        self.descendre("Descend à la boutique, rideau baissé : c'est lundi.", "Ménage de la boutique", "rt-lundi")
        T, R = "Ménage de la boutique", "rt-lundi"
        self.emettre({"action": "Allume la boutique, sort le seau et la serpillière de la réserve.", "piece": "boutique", "via": ["reserve"], "charge": "simple",
                      "app": {"allume": ["lumiere-boutique"]}}, T, R)
        textes = ["Lave le sol de la boutique.", "Nettoie la vitrine réfrigérée.", "Dépoussière les rayons du haut.", "Fait les vitres de la vitrine."]
        while self.i < idx("10:30"):
            if self.besoin_pressant(T, R):
                continue
            self.emettre({"action": choix(textes, self.date, self.i), "piece": "boutique", "mode": "effort", "charge": "simple"}, T, R)
        T = "Comptes de la semaine"
        self.emettre({"action": "Éteint la boutique et s'installe au bureau de l'arrière-boutique avec le cahier des comptes, les lunettes sur le nez.",
                      "piece": "arriere-boutique", "posture": "assis", "charge": "precision", "app": {"eteint": ["lumiere-boutique"]},
                      "objets": [{"objet": "obj-lunettes", "de": self.sim.positions["obj-lunettes"], "vers": "sur son nez"}]}, T, R)
        while self.i < idx("12:15") - 1:
            if self.besoin_pressant(T, R):
                continue
            self.emettre(self.preoccupation({"action": choix(["Additionne les recettes de la semaine dernière.", "Classe les factures du grossiste.",
                                                              "Fait le total du carnet des ardoises.", "Compare avec mars de l'an dernier."],
                                                             self.date, self.i),
                                             "piece": "arriere-boutique", "posture": "assis", "mode": "travail", "charge": "precision"}), T, R)
        self.emettre({"action": "Referme le cahier des comptes, remonte ses lunettes sur le front.", "piece": "arriere-boutique", "posture": "assis",
                      "charge": "simple", "ev": ["comptes_faits"],
                      "objets": [{"objet": "obj-lunettes", "de": "sur son nez", "vers": "sur son front"}]}, T, R)
        self.faits.append("Comptes de la semaine faits")
        self.monter("cuisine", "Monte à l'appartement.", "Pause de midi", "rt-repas")
        d, f = self.R["dejeuner"]["lundi"]
        self.repas(d, f, "dejeuner")
        self.sieste(self.R["sieste"]["lundi"][1])
        self.descendre("Redescend à la réserve.", "Réserve", "rt-lundi")
        T = "Réserve et commande"
        while self.i < idx("16:30") - 1:
            if self.besoin_pressant(T, R):
                continue
            self.emettre(self.preoccupation({"action": choix(["Range les étagères de la réserve.", "Compte les cartons de conserves.",
                                                              "Note sur le bon de commande ce qui manque pour mardi.", "Aplatit les cartons vides."],
                                                             self.date, self.i),
                                             "piece": "reserve", "mode": "travail", "charge": "simple"}), T, R)
        self.faits.append("Bon de commande prêt pour le grossiste")
        pos = self.sim.positions
        self.emettre({"action": "Raccroche sa blouse, éteint, remonte et accroche ses clés au portemanteau.", "piece": "couloir", "charge": "simple",
                      "escalier": {"sens": "montee"},
                      "objets": [{"objet": "obj-blouse", "de": pos["obj-blouse"], "vers": "arriere-boutique / patère"},
                                 {"objet": "obj-cles", "de": pos["obj-cles"], "vers": "couloir / portemanteau"}]}, "Fin de journée", R)
        self.apres_midi_libre(idx(self.R["diner"]["lundi"][0]))
        d, f = self.R["diner"]["lundi"]
        self.repas(d, f, "diner")
        toilette = idx(self.R["toilette_soir"]["defaut"])
        self.television(toilette)
        self.coucher(toilette, idx(self.R["extinction"]["defaut"]))

    def vivre(self):
        if self.ouverture():
            self.journee_commerce()
        else:
            self.journee_fermeture()
        return self.terminer()

    def terminer(self):
        if self.i != PAS_PAR_JOUR:
            raise Incoherence(f"la journée de l'agent compte {self.i} pas")
        etat_final, stats = self.sim.terminer(self.j.extinction, self.j.endormissement)
        etat_final["agent"] = self.mem
        self.j.ecarts = self.decisions
        self.j.bilan = [f"**{f}**" for f in self.faits] or ["Journée sans fait marquant."]
        for s in self.j.segments:
            s.pop("_bloc", None)
        return self.sim.steps, etat_final, stats
