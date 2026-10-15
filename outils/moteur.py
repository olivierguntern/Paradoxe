"""Moteur de calcul des journées de Paradoxe.

Le contenu d'une journée (actions, pensées, rêves, événements vécus, objets,
appareils) est rédigé dans outils/journees/<personnage>/<date>.py. Ce moteur calcule, avec
les règles de la fiche du personnage : déplacements, lumière, besoins,
émotions et concentration. Il vérifie aussi que chaque objet déplacé se
trouvait bien là où la journée le prend, d'un jour à l'autre.
"""
import heapq
import json

from perception import Perception

PAS_PAR_JOUR = 288


# ---------------------------------------------------------------- temps
def hm(i):
    m = i * 5
    return f"{m // 60:02d}:{m % 60:02d}"


def idx(h):
    a, b = map(int, h.split(":"))
    return (a * 60 + b) // 5


# ---------------------------------------------------------------- rédaction
def p(action, pensee=None, **kw):
    """Un pas de 5 minutes. Options : ev, objets, nouveaux_objets, consommation, production,
    achats, argent, effets, app, radio, musique, tele, mode, charge, posture, piece, lieu, via,
    via_apres, sortie, retour, escalier, parcours, phase_sommeil, reve, poste (endroit précis de la pièce, ou
    liste d'arrêts successifs : rayons d'une boutique…), visiteurs (clients du pas, pour la vue) ; pour un commerçant :
    ventes, livraisons, reprises, prelevements, clients."""
    d = {"action": action, "pensee": pensee}
    d.update(kw)
    return d


def mv(objet, de, vers):
    return {"objet": objet, "de": de, "vers": vers}


def c(produit, quantite):
    """Consommation d'une provision (identifiant de la fiche, quantité dans son unité)."""
    return {"produit": produit, "quantite": quantite}


def pr(produit, quantite):
    """Production d'un plat préparé (identifiant de produits_prepares)."""
    return {"produit": produit, "quantite": quantite}


def on(*a):
    return {"allume": list(a)}


def off(*a):
    return {"eteint": list(a)}


def onoff(allume=(), eteint=()):
    return {"allume": list(allume), "eteint": list(eteint)}


def course(distance_m, denivele_m=0):
    return {"moyen": "course", "distance_m": distance_m, "denivele_m": denivele_m}


def marche(distance_m, denivele_m=0):
    return {"moyen": "marche", "distance_m": distance_m, "denivele_m": denivele_m}


def voiture(distance_m, denivele_m=0):
    return {"moyen": "voiture", "distance_m": distance_m, "denivele_m": denivele_m}


def vente(produit, quantite, paiement="especes"):
    """Vente au comptoir : quantité en unités de vente du catalogue, payée en espèces (caisse) ou par carte (compte)."""
    return {"produit": produit, "quantite": quantite, "paiement": paiement}


class Journee:
    def __init__(self, date, jour, extinction, endormissement=15):
        self.date = date
        self.jour = jour
        self.extinction = extinction  # heure où il éteint pour dormir
        self.endormissement = endormissement  # minutes entre l'extinction et le sommeil
        self.segments = []
        self.ecarts = []
        self.bilan = []
        self.resume = {}

    def seg(self, debut, titre, piece, routine, mode, charge, posture, pas, lieu="domicile"):
        self.segments.append(dict(debut=debut, titre=titre, piece=piece, routine=routine, mode=mode,
                                  charge=charge, posture=posture, pas=pas, lieu=lieu))


# ---------------------------------------------------------------- état
def argent_initial(fiche):
    """Espèces, compte courant et, pour un commerçant, caisse et coffre du magasin au premier pas."""
    E = fiche.get("economie", {})
    out = {"especes": E.get("especes_au_debut", 0), "compte": E.get("compte_courant_au_debut", 0)}
    if "caisse_au_debut" in E:
        out["caisse"] = E["caisse_au_debut"]
    if "coffre_au_debut" in E:
        out["coffre"] = E["coffre_au_debut"]
    if "ardoises_au_debut" in E:
        out["ardoises"] = round(sum(E["ardoises_au_debut"].values()), 2)
    return out


def boutique_initiale(fiche):
    """Stock du magasin au premier pas, produit par produit (unités de vente du catalogue)."""
    return {c["produit"]: c["stock_initial"] for c in fiche.get("commerce", {}).get("catalogue", [])}


def position_initiale(o):
    """Position d'un objet de la fiche au premier pas, telle que la simulation la suit (« pièce / support »)."""
    e = o["emplacement_initial"]
    return f"{e['piece']} / {e['support']}" if e["lieu"] == "domicile" else f"{e['lieu']} / {e['piece']} / {e['support']}"


def etat_initial_depuis_fiche(fiche):
    positions = {o["id"]: position_initiale(o) for o in fiche["objets"]}
    emo = dict(fiche["etat_initial"]["emotions"])
    conc = emo.pop("concentration")
    stock = {x["id"]: x["quantite"] for x in fiche["domicile"]["provisions_au_debut"] if x.get("suivi", True)}
    etat = {"piece": fiche["etat_initial"]["piece"], "besoins": dict(fiche["etat_initial"]["besoins"]),
            "emotions": emo, "concentration": conc, "lumieres": {}, "appareils": [], "positions": positions, "cafe": [],
            "stock": stock, "argent": argent_initial(fiche)}
    if "commerce" in fiche:
        etat["boutique"] = boutique_initiale(fiche)
    return etat


def etat_depuis_veille(chemin_json):
    return json.load(open(chemin_json, encoding="utf-8"))["etat_final"]


# ---------------------------------------------------------------- simulation
class Incoherence(Exception):
    pass


def _clamp(v, hi=100.0):
    return max(0.0, min(hi, v))


class Simulation:
    """Applique les règles de la fiche pas à pas.

    Utilisée de deux façons : pour une journée rédigée (simuler) et par
    l'agent autonome, qui consulte l'état avant de décider de chaque pas.
    """

    def __init__(self, fiche, date, etat, perturbations=None):
        self.fiche = fiche
        self.date = date
        self.B = fiche["besoins"]
        M = fiche["modele_emotionnel"]
        self.EV = M["evenements"]
        self.NEVRO = fiche["personnalite"]["big_five"]["nevrosisme"]
        self.PIECES = {pc["id"]: pc for pc in fiche["domicile"]["pieces"]}
        self.PLAN = fiche["domicile"]["plan"]
        self.IMM = fiche["immeuble"]
        eph = fiche["meta"]["ephemerides_lyon_approximatives"][date]
        self.LEVER, self.COUCHER = idx(eph["lever_soleil"]), idx(eph["coucher_soleil"])
        self.HL = M["demi_vie_pas"]
        self.CIBLES = M["concentration"]["cibles"]
        self.DP = self.PLAN["deplacements_dans_la_piece"]
        self.PRODUITS = {x["id"]: x for x in fiche["domicile"]["provisions_au_debut"] + fiche["domicile"]["produits_prepares"]}
        self.graph = {}
        for l in self.PLAN["liaisons"]:
            self.graph.setdefault(l["a"], []).append((l["b"], l["distance_m"]))
            self.graph.setdefault(l["b"], []).append((l["a"], l["distance_m"]))
        # escalier intérieur (maison sur deux niveaux) : compté dès qu'un chemin l'emprunte
        self.ESCALIERS = {frozenset((l["a"], l["b"])) for l in self.PLAN["liaisons"] if l.get("escalier")}
        self.CATALOGUE = {x["produit"]: x for x in fiche.get("commerce", {}).get("catalogue", [])}

        self.besoins = dict(etat["besoins"])
        self.emo = dict(etat["emotions"])
        self.conc = etat["concentration"]
        self.lumieres = {pc: bool(etat["lumieres"].get(pc)) for pc in self.PIECES}
        self.appareils = set(etat["appareils"])
        self.positions = dict(etat["positions"])
        # ce que le personnage croit : égal à la réalité, sauf écarts hérités de la veille
        self.croyances = dict(self.positions) | dict(etat.get("croyances") or {})
        # changements du monde faits à son insu (scénario), appliqués au début de leur pas
        self.perturbations = [x for x in (perturbations or []) if x["date"] == date]
        self.monde = {}
        self.cafe = list(etat["cafe"])
        self.stock = dict(etat["stock"])
        self.argent = dict(etat.get("argent") or argent_initial(fiche))
        self.boutique = dict(etat["boutique"]) if etat.get("boutique") is not None else (boutique_initiale(fiche) if self.CATALOGUE else None)
        self.base = {k: v for k, v in M["etat_de_base"].items() if k != "solitude"}
        self.piece = etat["piece"]
        self.stats = {"entre_pieces_m": 0.0, "dans_les_pieces_m": 0.0, "exterieur_m": 0.0, "foulees": 0.0,
                      "passages_de_piece": 0, "marches": 0, "denivele_positif_m": 0, "denivele_negatif_m": 0, "lumiere_allumages": 0,
                      "voiture_m": 0.0}
        self.steps = []
        self.PERCEPTION = Perception(fiche, self) if fiche.get("perception") else None

    # ------------------------------------------------------------ outils
    def chemin(self, a, b):
        dist, prev, q = {a: 0}, {}, [(0, a)]
        while q:
            d, u = heapq.heappop(q)
            if u == b:
                break
            for v, w in self.graph[u]:
                if d + w < dist.get(v, 1e9):
                    dist[v], prev[v] = d + w, u
                    heapq.heappush(q, (d + w, v))
        path = [b]
        while path[-1] != a:
            path.append(prev[path[-1]])
        return path[::-1], dist[b]

    def besoin_lumiere(self, piece, i):
        return piece in self.PIECES and (not self.PIECES[piece]["fenetre"] or i < self.LEVER or i >= self.COUCHER)

    def eclairage_auto(self, piece):
        """Faux pour une pièce dont l'éclairage ne se commande qu'explicitement (boutique éclairée pendant l'ouverture)."""
        return self.PIECES.get(piece, {}).get("eclairage") != "permanent"

    @staticmethod
    def negatif(e, d):
        return (d > 0 and e in ("tristesse", "anxiete", "colere", "solitude")) or (d < 0 and e in ("joie", "fierte"))

    def latence_endormissement(self, emotions):
        """Durée d'endormissement (minutes) selon l'état émotionnel au moment d'éteindre."""
        SOM = self.fiche["sante"]["sommeil"]
        trop = emotions["anxiete"] > SOM["seuil_anxiete_insomnie"] or emotions["excitation"] > SOM["seuil_excitation_insomnie"]
        return SOM["endormissement_minutes_si_anxieux"] if trop else SOM["endormissement_minutes_normal"]

    def changements_du_monde(self):
        """Applique, une seule fois, les perturbations prévues au pas qui commence (la réalité change, pas les croyances)."""
        i = len(self.steps)
        if i not in self.monde:
            self.monde[i] = []
            for x in self.perturbations:
                if idx(x["heure"]) == i:
                    if x["objet"] not in self.positions:
                        raise Incoherence(f"{hm(i)} : perturbation sur un objet inconnu {x['objet']}")
                    self.monde[i].append({"objet": x["objet"], "de": self.positions[x["objet"]], "vers": x["vers"], "par": x.get("par", "voyageur")})
                    self.positions[x["objet"]] = x["vers"]
        return self.monde[i]

    # ------------------------------------------------------------ un pas
    def pas(self, st, s):
        """Applique un pas rédigé (st) dans son segment (s) et renvoie l'entrée de la timeline."""
        B, PLAN, IMM, PIECES = self.B, self.PLAN, self.IMM, self.PIECES
        besoins, emo, lumieres, appareils, st_ = self.besoins, self.emo, self.lumieres, self.appareils, self.stats
        i = len(self.steps)
        monde = self.changements_du_monde()
        piece = st.get("piece", s["piece"])
        lieu = st.get("lieu", s["lieu"])
        mode = st.get("mode", s["mode"])
        charge = st.get("charge", s["charge"])
        posture = st.get("posture", s["posture"])
        radio = st.get("radio", False)
        endormi = mode == "sommeil"
        lum = []

        # ---- déplacements dans l'appartement
        depart = self.piece
        arrivee = piece
        if st.get("sortie"):
            arrivee = st["sortie"] if isinstance(st["sortie"], str) else "palier"
        if st.get("retour"):
            depart = st["retour"] if isinstance(st["retour"], str) else "palier"
        etapes = [depart] + st.get("via", []) + [arrivee] + st.get("via_apres", [])
        if st.get("via_apres"):
            etapes.append(arrivee)
        parcours_app = [depart]
        dist = 0.0
        for a, b in zip(etapes, etapes[1:]):
            if a == b or a not in self.graph or b not in self.graph:
                continue
            pth, d = self.chemin(a, b)
            parcours_app += pth[1:]
            dist += d
        dep = {}
        if len(parcours_app) > 1:
            dep.update({"chemin": parcours_app, "distance_m": round(dist, 1),
                        "duree_s": round(dist / PLAN["vitesse_marche_m_s"]),
                        "foulees": round(dist / PLAN["longueur_foulee_m"])})
            st_["entre_pieces_m"] += dist
            st_["foulees"] += dist / PLAN["longueur_foulee_m"]
            st_["passages_de_piece"] += len(parcours_app) - 1
            aller_retour = parcours_app[-1] == parcours_app[0]
            for a, b in zip(parcours_app, parcours_app[1:]):
                if lumieres.get(a) and self.eclairage_auto(a) and not (aller_retour and a == parcours_app[0]):
                    lumieres[a] = False
                    lum.append(f"éteint la lumière ({a})")
                if self.besoin_lumiere(b, i) and self.eclairage_auto(b) and not lumieres[b] and not (aller_retour and b == parcours_app[0]):
                    lumieres[b] = True
                    st_["lumiere_allumages"] += 1
                    lum.append(f"allume la lumière ({b})")
        elif not endormi and i == self.COUCHER and self.besoin_lumiere(piece, i) and self.eclairage_auto(piece) and not lumieres[piece]:
            lumieres[piece] = True
            st_["lumiere_allumages"] += 1
            lum.append(f"allume la lumière ({piece}) : la nuit tombe")

        # ---- escalier et parcours extérieur
        effets_escalier = {}
        passages = [(a, b) for a, b in zip(parcours_app, parcours_app[1:]) if frozenset((a, b)) in self.ESCALIERS]
        if passages:
            dimm = IMM["deplacement"]
            marches, duree = 0, 0
            for a, b in passages:
                monte = PIECES.get(b, {}).get("niveau", 0) > PIECES.get(a, {}).get("niveau", 0)
                marches += IMM["marches_par_etage"]
                duree += IMM["marches_par_etage"] * dimm["montee_secondes_marche"] / IMM["marches_total"] if monte else dimm["descente_secondes"]
                for n, v in (dimm["effets_montee"] if monte else dimm["effets_descente"]).items():
                    effets_escalier[n] = effets_escalier.get(n, 0) + v
            a, b = passages[0]
            sens = "montee" if PIECES.get(b, {}).get("niveau", 0) > PIECES.get(a, {}).get("niveau", 0) else "descente"
            dep["escalier"] = {"sens": sens, "etages": 1, "marches": marches, "duree_s": round(duree), "interieur": True} | (
                {"passages": len(passages)} if len(passages) > 1 else {})
            st_["marches"] += marches
            st_["foulees"] += marches
        if "escalier" in st:
            sens = st["escalier"]["sens"]
            dimm = IMM["deplacement"]
            duree = dimm["descente_secondes"] if sens == "descente" else (
                dimm["montee_secondes_apres_course"] if st["escalier"].get("apres_course") else dimm["montee_secondes_marche"])
            dep["escalier"] = {"sens": sens, "etages": IMM["etage_appartement"], "marches": IMM["marches_total"], "duree_s": duree}
            st_["marches"] += IMM["marches_total"]
            st_["foulees"] += IMM["marches_total"]
            effets_escalier = dimm["effets_descente"] if sens == "descente" else dimm["effets_montee"]
        if "parcours" in st:
            dep["parcours"] = st["parcours"]
            a_pied = [x for x in st["parcours"] if x["moyen"] != "voiture"]
            for seg_ in st["parcours"]:
                if seg_["moyen"] == "voiture":
                    st_["voiture_m"] += seg_["distance_m"]
                    continue
                st_["exterieur_m"] += seg_["distance_m"]
                st_["foulees"] += seg_["distance_m"] / (PLAN["longueur_foulee_course_m"] if seg_["moyen"] == "course" else PLAN["longueur_foulee_m"])
                if seg_["denivele_m"] > 0:
                    st_["denivele_positif_m"] += seg_["denivele_m"]
                else:
                    st_["denivele_negatif_m"] += -seg_["denivele_m"]
            if a_pied:
                dep["foulees_exterieur"] = round(sum(
                    x["distance_m"] / (PLAN["longueur_foulee_course_m"] if x["moyen"] == "course" else PLAN["longueur_foulee_m"])
                    for x in a_pied))

        # ---- appareils et lumières commandés explicitement
        for a in st.get("app", {}).get("allume", []):
            if a.startswith("lumiere-"):
                if not lumieres[a[8:]]:
                    lumieres[a[8:]] = True
                    st_["lumiere_allumages"] += 1
                    lum.append(f"allume la lumière ({a[8:]})")
            else:
                appareils.add(a)
        for a in st.get("app", {}).get("eteint", []):
            if a.startswith("lumiere-"):
                if lumieres[a[8:]]:
                    lumieres[a[8:]] = False
                    lum.append(f"éteint la lumière ({a[8:]})")
            else:
                appareils.discard(a)
        self.piece = piece

        # ---- petits déplacements dans la pièce
        if piece in PIECES:
            intra = self.DP["metres_par_pas"][charge] * (self.DP["facteur_assis_ou_allonge"] if posture in ("assis", "allongé") else 1.0)
            st_["dans_les_pieces_m"] += intra
            st_["foulees"] += intra / PLAN["longueur_foulee_m"]

        # ---- objets : création éventuelle, puis chaque déplacement doit partir de la position connue
        for o in st.get("nouveaux_objets", []):
            if o["id"] in self.positions:
                raise Incoherence(f"{hm(i)} : l'objet {o['id']} existe déjà")
            self.positions[o["id"]] = self.croyances[o["id"]] = o["position"]
        for o in st.get("objets", []):
            if o["objet"] not in self.positions:
                raise Incoherence(f"{hm(i)} : objet inconnu {o['objet']}")
            if self.positions[o["objet"]] != o["de"]:
                raise Incoherence(f"{hm(i)} : {o['objet']} est à « {self.positions[o['objet']]} », pas à « {o['de']} »")
            self.positions[o["objet"]] = self.croyances[o["objet"]] = o["vers"]

        # ---- provisions : achats et production, puis consommation, jamais en dessous de zéro
        mouvements = {}
        for sens, cle in ((1, "achats"), (1, "production"), (-1, "consommation")):
            for x in st.get(cle, []):
                pid, q = x["produit"], x["quantite"]
                if pid not in self.PRODUITS:
                    raise Incoherence(f"{hm(i)} : produit inconnu {pid}")
                spec = self.PRODUITS[pid]
                ligne = {"produit": pid, "nom": spec["produit"], "quantite": q, "unite": spec["unite"]}
                if "prix" in x:
                    ligne["prix"] = x["prix"]
                if spec.get("suivi", True):
                    self.stock[pid] = self.stock.get(pid, 0) + sens * q
                    if self.stock[pid] < 0:
                        raise Incoherence(f"{hm(i)} : il ne reste pas assez de « {spec['produit']} » ({self.stock[pid] + q} {spec['unite']} pour {q} demandés)")
                    ligne["reste"] = self.stock[pid]
                mouvements.setdefault(cle, []).append(ligne)

        # ---- magasin : livraisons et reprises, prélèvements pour la maison, puis ventes ; jamais en dessous de zéro
        argent = dict(st.get("argent", {}))
        if any(k in st for k in ("livraisons", "reprises", "prelevements", "ventes")):
            if self.boutique is None:
                raise Incoherence(f"{hm(i)} : pas de magasin dans la fiche")
            def sortir(pid, q, quoi):
                if pid not in self.CATALOGUE:
                    raise Incoherence(f"{hm(i)} : produit inconnu au catalogue {pid}")
                self.boutique[pid] = self.boutique.get(pid, 0) - q
                if self.boutique[pid] < 0:
                    raise Incoherence(f"{hm(i)} : {quoi} de {q} « {self.CATALOGUE[pid]['nom']} », il n'en reste que {self.boutique[pid] + q} en magasin")
            for cle, sens in (("reprises", -1), ("livraisons", 1)):
                for x in st.get(cle, []):
                    pid, q = x["produit"], x["quantite"]
                    if sens < 0:
                        sortir(pid, q, "reprise")
                    else:
                        if pid not in self.CATALOGUE:
                            raise Incoherence(f"{hm(i)} : produit inconnu au catalogue {pid}")
                        self.boutique[pid] = self.boutique.get(pid, 0) + q
                    mouvements.setdefault(cle, []).append({"produit": pid, "nom": self.CATALOGUE[pid]["nom"], "quantite": q,
                                                           "reste": self.boutique[pid]} | ({"motif": x["motif"]} if x.get("motif") else {}))
            for x in st.get("prelevements", []):
                pid, q = x["produit"], x["quantite"]
                sortir(pid, q, "prélèvement")
                mid, qm = x["maison"], x["quantite_maison"]
                if mid not in self.PRODUITS:
                    raise Incoherence(f"{hm(i)} : provision inconnue {mid}")
                self.stock[mid] = self.stock.get(mid, 0) + qm
                mouvements.setdefault("prelevements", []).append({"produit": pid, "nom": self.CATALOGUE[pid]["nom"], "quantite": q,
                                                                  "reste": self.boutique[pid], "maison": mid, "quantite_maison": qm,
                                                                  "reste_maison": self.stock[mid]})
            recu = {}
            for x in st.get("ventes", []):
                pid, q = x["produit"], x["quantite"]
                sortir(pid, q, "vente")
                montant = round(q * self.CATALOGUE[pid]["prix"], 2)
                compte = {"especes": "caisse", "carte": "compte", "ardoise": "ardoises"}[x["paiement"]]
                recu[compte] = round(recu.get(compte, 0) + montant, 2)
                mouvements.setdefault("ventes", []).append({"produit": pid, "nom": self.CATALOGUE[pid]["nom"], "quantite": q,
                                                            "prix": montant, "paiement": x["paiement"], "reste": self.boutique[pid]})
            for compte, m in recu.items():
                argent[compte] = round(argent.get(compte, 0) + m, 2)
        if st.get("clients"):
            mouvements["clients"] = st["clients"]

        # ---- argent : espèces, compte, caisse, coffre ; seul le compte peut passer sous zéro
        if argent:
            for compte, montant in argent.items():
                self.argent[compte] = round(self.argent.get(compte, 0) + montant, 2)
                if compte != "compte" and self.argent[compte] < 0:
                    raise Incoherence(f"{hm(i)} : pas assez d'argent ({compte}) pour {-montant} €")
            mouvements["argent"] = {"mouvements": argent, "soldes": dict(self.argent)}

        # ---- besoins
        def var(n, cle):
            return B[n]["variation_par_pas"].get(cle, B[n]["variation_par_pas"]["eveille"])
        if endormi:
            for n in ("faim", "soif", "energie", "hygiene", "toilettes"):
                besoins[n] += B[n]["variation_par_pas"]["endormi"]
        else:
            effort = mode == "effort"
            besoins["faim"] += var("faim", "effort_physique" if effort else "eveille")
            besoins["soif"] += var("soif", "effort_physique" if effort else "eveille")
            besoins["energie"] += B["energie"]["variation_par_pas"]["sieste" if mode == "sieste" else ("effort_physique" if effort else "eveille")]
            besoins["hygiene"] += var("hygiene", "effort_physique" if effort else "eveille")
            besoins["toilettes"] += B["toilettes"]["variation_par_pas"]["eveille"]
            if mode != "sieste":
                tele = st.get("tele")
                besoins["social"] += B["social"]["variation_par_pas"]["eveille"] + (B["social"]["satisfaction"]["radio_par_pas"] if radio else 0) + (
                    B["social"]["satisfaction"]["match_televise_par_pas"] if tele == "match" else (B["social"]["satisfaction"]["television_par_pas"] if tele else 0))
                if mode == "travail":
                    besoins["detente"] += B["detente"]["variation_par_pas"]["travail"]
                elif mode == "loisir":
                    besoins["detente"] += B["detente"]["satisfaction"]["loisir_par_pas"]
                elif mode == "lecture":
                    besoins["detente"] += B["detente"]["satisfaction"]["lecture_par_pas"]
                elif effort:
                    besoins["detente"] += B["detente"]["satisfaction"]["course_par_pas"]
                else:
                    musique = radio or st.get("musique", False)
                    besoins["detente"] += B["detente"]["variation_par_pas"]["eveille_autre"] + (B["detente"]["satisfaction"]["musique_par_pas"] if musique else 0)
        for n, v in effets_escalier.items():
            besoins[n] += v
        for n, v in st.get("effets", {}).items():
            if n == "cafe":
                self.cafe.append(i)
            elif v == "vide":
                besoins[n] = 100
            else:
                besoins[n] += v
        for n in besoins:
            besoins[n] = _clamp(besoins[n])
        bonus = sum(8 if c <= i < c + 24 else (-4 if c + 24 <= i < c + 36 else 0) for c in self.cafe)

        # ---- perception : ce qu'il voit, entend et remarque ; une remarque corrige sa croyance et se vit comme un événement
        perception, ev_perception = None, []
        if self.PERCEPTION:
            perception, ev_perception = self.PERCEPTION.percevoir(i, lieu, piece, parcours_app, endormi, {o["objet"] for o in st.get("objets", [])})

        # ---- émotions : retour vers la base, événements, besoins
        self.base["solitude"] = 0.25 + 0.01 * max(0.0, 75 - besoins["social"])
        for e in emo:
            hl = self.HL[e] / (2 if endormi else 1)
            emo[e] = self.base[e] + (emo[e] - self.base[e]) * 0.5 ** (1 / hl)
        ev_out = []
        bonus_conc = 0.0
        for ev in st.get("ev", []) + [e for e in ev_perception if e not in st.get("ev", [])]:
            if ev not in self.EV:
                raise Incoherence(f"{hm(i)} : événement inconnu {ev}")
            spec = self.EV[ev]
            pensee = ev.startswith("pensee") or ev.startswith("souvenir") or ev == "anticipation_delicate"
            rum = 1.5 if pensee and i >= idx("22:30") and posture == "allongé" else 1.0
            appl = {}
            for e, d in spec["effets"].items():
                dd = d * rum * ((0.5 + self.NEVRO) if self.negatif(e, d) else 1.0)
                emo[e] += dd
                appl[e] = round(dd, 3)
            bonus_conc += spec.get("concentration", 0)
            ev_out.append({"id": ev, "effets": appl} | ({"rumination": True} if rum > 1 else {}))
        if not endormi:
            if besoins["faim"] < 35:
                emo["colere"] += 0.01
                emo["joie"] -= 0.005
            if besoins["energie"] < 30:
                emo["joie"] -= 0.005
                emo["colere"] += 0.005
            if besoins["toilettes"] < 25:
                emo["anxiete"] += 0.01
            if besoins["detente"] < 30:
                emo["colere"] += 0.005
        for e in emo:
            emo[e] = _clamp(emo[e], 1.0)
        cible = self.CIBLES[charge]
        if besoins["energie"] < 30:
            cible -= 0.15
        if emo["anxiete"] > 0.5 or emo["tristesse"] > 0.5:
            cible -= 0.1
        if besoins["toilettes"] < 25:
            cible -= 0.1
        self.conc = _clamp(self.conc + (max(0, cible) - self.conc) * 0.5 + bonus_conc, 1.0)

        entry = {"pas": i, "heure": hm(i), "lieu": lieu, "piece": piece, "posture": posture,
                 "routine": s["routine"], "activite": s["titre"], "action": st["action"], "pensee": st["pensee"]}
        if dep:
            entry["deplacement"] = dep
        for opt in ("phase_sommeil", "reve", "nouveaux_objets", "objets", "ruptures", "poste", "visiteurs", "ensemble", "croise", "conversation"):
            if st.get(opt):
                entry[opt] = st[opt]
        entry.update(mouvements)
        if perception:
            entry["perception"] = perception
        if monde:
            entry["monde"] = monde
        if lum:
            entry["lumiere"] = lum
        entry["appareils_allumes"] = sorted(appareils) + [f"lumiere-{pc}" for pc, v in lumieres.items() if v]
        if ev_out:
            entry["evenements"] = ev_out
        entry["besoins"] = {n: round(v, 1) for n, v in besoins.items()} | {"energie_ressentie": round(_clamp(besoins["energie"] + bonus), 1)}
        entry["emotions"] = {e: round(v, 3) for e, v in emo.items()} | {"concentration": round(self.conc, 3)}
        self.steps.append(entry)
        return entry

    # ------------------------------------------------------------ fin de journée
    def terminer(self, extinction, endormissement):
        st_ = self.stats
        if len(self.steps) != PAS_PAR_JOUR:
            raise Incoherence(f"la journée compte {len(self.steps)} pas au lieu de {PAS_PAR_JOUR}")
        SOM = self.fiche["sante"]["sommeil"]
        seuil, seuil_exc = SOM["seuil_anxiete_insomnie"], SOM["seuil_excitation_insomnie"]
        emo_ext = self.steps[idx(extinction)]["emotions"]
        attendu_min = self.latence_endormissement(emo_ext)
        if endormissement != attendu_min:
            raise Incoherence(f"à l'extinction ({extinction}), anxiété {emo_ext['anxiete']} et excitation {emo_ext['excitation']} : "
                              f"l'endormissement devrait durer {attendu_min} minutes, la journée en prévoit {endormissement}")
        etat_final = {"piece": self.piece, "besoins": {n: round(v, 4) for n, v in self.besoins.items()},
                      "emotions": {e: round(v, 4) for e, v in self.emo.items()}, "concentration": round(self.conc, 4),
                      "lumieres": {pc: v for pc, v in self.lumieres.items() if v}, "appareils": sorted(self.appareils),
                      "positions": self.positions, "cafe": [c - PAS_PAR_JOUR for c in self.cafe if c + 36 > PAS_PAR_JOUR],
                      "stock": self.stock, "argent": self.argent}
        if self.boutique is not None:
            etat_final["boutique"] = self.boutique
        if self.PERCEPTION:
            etat_final["croyances"] = {k: v for k, v in self.croyances.items() if self.positions.get(k) != v}
        st_["anxiete_extinction"] = emo_ext["anxiete"]
        st_["excitation_extinction"] = emo_ext["excitation"]
        st_["seuil_insomnie"] = seuil
        st_["seuil_excitation"] = seuil_exc
        st_["endormissement_min"] = attendu_min
        return etat_final, st_


def simuler(fiche, j, etat):
    """Calcule une journée rédigée à la main."""
    sim = Simulation(fiche, j.date, etat)
    for s in j.segments:
        if idx(s["debut"]) != len(sim.steps):
            raise Incoherence(f"segment « {s['titre']} » commence à {s['debut']} au lieu de {hm(len(sim.steps))}")
        for st in s["pas"]:
            sim.pas(st, s)
    etat_final, stats = sim.terminer(j.extinction, j.endormissement)
    return sim.steps, etat_final, stats


# ---------------------------------------------------------------- sorties
def bilan_magasin(fiche, steps, etat_final):
    """Ventes, livraisons, reprises et prélèvements du jour, produit par produit."""
    cat = fiche["commerce"]["catalogue"]
    P = {c["produit"]: {"nom": c["nom"], "vendu": 0, "livre": 0, "repris": 0, "preleve": 0, "recette": 0.0,
                        "stock": etat_final["boutique"].get(c["produit"], 0)} for c in cat}
    esp = carte = ardoise = 0.0
    clients = 0
    ruptures = []
    for s in steps:
        for x in s.get("ventes", []):
            P[x["produit"]]["vendu"] += x["quantite"]
            P[x["produit"]]["recette"] = round(P[x["produit"]]["recette"] + x["prix"], 2)
            if x["paiement"] == "especes":
                esp += x["prix"]
            elif x["paiement"] == "carte":
                carte += x["prix"]
            else:
                ardoise += x["prix"]
        for cle, champ in (("livraisons", "livre"), ("reprises", "repris"), ("prelevements", "preleve")):
            for x in s.get(cle, []):
                P[x["produit"]][champ] += x["quantite"]
        clients += s.get("clients", 0)
        for r in s.get("ruptures", []):
            if r not in ruptures:
                ruptures.append(r)
    return {"clients": clients, "recette": round(esp + carte + ardoise, 2), "recette_especes": round(esp, 2), "recette_carte": round(carte, 2),
            "a_credit": round(ardoise, 2), "ruptures": ruptures, "produits": P}


def bilan_perception(fiche, steps, etat_final):
    """Ce qu'il a remarqué et entendu dans la journée, ce qui a changé à son insu, ce qu'il croit à tort le soir."""
    noms = {o["id"]: o["nom"] for o in fiche["objets"]}
    vus, pas_vus, entendu, remarques, insu = set(), 0, {}, [], []
    for s in steps:
        P = s.get("perception") or {}
        if P.get("vu"):
            pas_vus += 1
            vus.update(P["vu"])
        for x in P.get("entend", []):
            entendu[x] = entendu.get(x, 0) + 1
        for r in P.get("remarques", []):
            nom = noms.get(r["objet"], r["objet"])
            if r["type"] == "absent":
                remarques.append(f"{s['heure']} — {nom} : n'est plus à « {r['croyait']} »")
            elif r["croyait"]:
                remarques.append(f"{s['heure']} — {nom} : à « {r['voit']} » au lieu de « {r['croyait']} »")
            else:
                remarques.append(f"{s['heure']} — {nom} : à nouveau en vue, à « {r['voit']} »")
        for m in s.get("monde", []):
            insu.append(f"{s['heure']} — {m['par']} : {noms.get(m['objet'], m['objet'])}, de « {m['de']} » vers « {m['vers']} »")
    return {"pas_avec_objets_vus": pas_vus, "objets_vus": len(vus), "entendu_pas": entendu, "remarques": remarques,
            "a_son_insu": insu, "croyances_fausses_en_fin_de_journee": etat_final.get("croyances", {})}


def quantite(q, unite):
    """« 1 steak », « 0 cuisse », « 3 steaks » : 0 et 1 au singulier, comme en français."""
    if unite is None:
        return "non suivi"
    if q in (0, 1) and unite.endswith("s") and unite not in ("g",):
        unite = unite[:-1]
    return f"{q} {unite}"


def ecrire(fiche, j, steps, etat_initial, etat_final, st_, chemin_json, chemin_md):
    B = fiche["besoins"]
    alertes = [f"{s['heure']} {n} = {v} (seuil {B[n]['seuil_alerte']})"
               for s in steps for n, v in s["besoins"].items() if n in B and v < B[n]["seuil_alerte"] and not s.get("phase_sommeil")]
    alertes_sommeil = {}
    for s in steps:
        if s.get("phase_sommeil"):
            for n, v in s["besoins"].items():
                if n in B and v < B[n]["seuil_alerte"]:
                    alertes_sommeil[n] = alertes_sommeil.get(n, 0) + 1
    conso, prod, achats, depenses = {}, {}, {}, {}
    for s in steps:
        for x in s.get("achats", []):
            achats.setdefault(x["nom"], [0, x["unite"], 0.0])
            achats[x["nom"]][0] += x["quantite"]
            achats[x["nom"]][2] += x.get("prix", 0)
        for compte, m in s.get("argent", {}).get("mouvements", {}).items():
            depenses[compte] = round(depenses.get(compte, 0) + m, 2)
    for s in steps:
        for x in s.get("consommation", []):
            conso.setdefault(x["nom"], [0, x["unite"]])[0] += x["quantite"]
        for x in s.get("production", []):
            prod.setdefault(x["nom"], [0, x["unite"]])[0] += x["quantite"]
    noms = {x["id"]: x for x in fiche["domicile"]["provisions_au_debut"] + fiche["domicile"]["produits_prepares"]}
    stock_fin = {noms[k]["produit"]: quantite(v, noms[k]["unite"]) for k, v in etat_final["stock"].items()}
    nb_ev = {}
    for s in steps:
        for e in s.get("evenements", []):
            nb_ev[e["id"]] = nb_ev.get(e["id"], 0) + 1
    deplaces = {}
    for s in steps:
        for o in s.get("objets", []):
            deplaces[o["objet"]] = o["vers"]
    total = st_["entre_pieces_m"] + st_["dans_les_pieces_m"] + st_["exterieur_m"]
    deplacements = {
        "entre_pieces_m": round(st_["entre_pieces_m"]), "dans_les_pieces_m_estimes": round(st_["dans_les_pieces_m"]),
        "exterieur_m": round(st_["exterieur_m"]), "total_m": round(total), "foulees_et_marches": round(st_["foulees"]),
        "passages_de_piece": st_["passages_de_piece"], "marches_d_escalier": st_["marches"],
        "denivele_positif_m": st_["denivele_positif_m"], "denivele_negatif_m": st_["denivele_negatif_m"]}
    if st_.get("voiture_m"):
        deplacements["voiture_m"] = round(st_["voiture_m"])
    magasin = bilan_magasin(fiche, steps, etat_final) if "boutique" in etat_final else None
    perception = bilan_perception(fiche, steps, etat_final) if fiche.get("perception") else None
    out = {
        "meta": {
            "personnage": fiche["meta"]["id"], "fiche_version": fiche["meta"]["version"],
            "date": j.date, "jour": j.jour, "pas_minutes": 5, "nombre_de_pas": PAS_PAR_JOUR,
            "methode": getattr(j, "methode", None) or [
                f"Rédigé à la main dans outils/journees/{getattr(j, 'personnage', fiche['meta']['id'])}/{j.date}.py : actions, pensées, rêves, événements vécus, objets déplacés, appareils utilisés.",
                "Calculé par outils/moteur.py avec les règles de la fiche : déplacements, lumière, besoins, émotions et concentration.",
                "Aucune émotion n'est fixée à la main : chaque variation provient d'un événement listé, d'un besoin ou du retour à l'état de base.",
                "La journée part de l'état exact de la fin de la veille (etat_initial), ou de la fiche pour le premier jour.",
            ],
            "champs": {
                "besoins, emotions": "valeurs à la fin du pas",
                "deplacement": "chemin dans l'appartement (distance, durée, foulées), escalier, parcours extérieur",
                "lumiere": "interrupteurs actionnés pendant le pas",
                "appareils_allumes": "appareils et lumières allumés à la fin du pas",
                "evenements": "événements vécus et effet appliqué sur chaque émotion (après modulation par la personnalité)",
                "besoins.energie_ressentie": "énergie corrigée de l'effet du café",
                **({"perception": "ce qu'il voit (objets remarqués), entend et remarque (écart entre ce qu'il croit et ce qu'il voit)",
                    "monde": "changements faits à son insu au début du pas (scénario)"} if fiche.get("perception") else {}),
            },
        },
        "resume": {
            "deplacements": deplacements,
            "lumiere": {"allumages": st_["lumiere_allumages"]},
            "evenements_vecus": nb_ev,
            **j.resume,
            "objets_deplaces_position_finale": deplaces,
            "provisions_consommees": {k: (quantite(v[0], v[1]) if v[1] else "utilisés (non suivis)") for k, v in conso.items()},
            "plats_prepares": {k: quantite(v[0], v[1]) for k, v in prod.items()},
            "achats": {k: f"{quantite(v[0], v[1])} ({v[2]:.2f} €)" for k, v in achats.items()},
            "argent": {"mouvements_du_jour": depenses, "soldes_en_fin_de_journee": etat_final.get("argent", {})},
            **({"magasin": magasin} if magasin else {}),
            "stock_en_fin_de_journee": stock_fin,
            "besoins_sous_le_seuil_d_alerte": alertes,
            "besoins_sous_le_seuil_pendant_le_sommeil_pas": alertes_sommeil,
            "endormissement": (f"extinction à {j.extinction} ; anxiété {st_['anxiete_extinction']} (seuil {st_['seuil_insomnie']}), "
                               f"excitation {st_['excitation_extinction']} (seuil {st_['seuil_excitation']}) : endormissement en {st_['endormissement_min']} minutes"),
            "ecarts_a_la_routine": j.ecarts,
            **({"perception": perception} if perception else {}),
        },
        "etat_initial": etat_initial,
        "etat_final": etat_final,
        "pas": steps,
    }
    json.dump(out, open(chemin_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    an, mo, jr = map(int, j.date.split("-"))
    L = [f"# {fiche['identite']['prenom']} {fiche['identite']['nom']} — {j.jour} {jr} {mois[mo - 1]} {an}\n",
         (f"Journée générée par l'agent autonome, pas à pas (5 minutes). Données complètes : `{j.date}.json`.\n" if getattr(j, "methode", None) else
          f"Journée rédigée pas à pas (5 minutes). Les déplacements, la lumière, les besoins et les émotions sont calculés avec les règles de la fiche. Données complètes : `{j.date}.json`.\n"),
         "## Déroulé\n", "| Heure | Lieu | Activité | Ce qu'il fait / pense | Événements vécus |", "|---|---|---|---|---|"]
    pos = 0
    for s in j.segments:
        n = len(s["pas"])
        bloc = steps[pos:pos + n]
        pos += n
        fin_h = hm(bloc[-1]["pas"] + 1) if bloc[-1]["pas"] < PAS_PAR_JOUR - 1 else "24:00"
        pens = list(dict.fromkeys(b["pensee"] for b in bloc if b.get("pensee")))
        reves = []
        for b in bloc:
            if b.get("reve") and b["reve"] not in reves:
                reves.append(b["reve"])
        if reves:
            txt = "Sommeil. Rêves : " + " / ".join(f"« {r} »" for r in reves)
        else:
            txt = bloc[0]["action"] + (" …" if n > 1 else "")
            if pens:
                txt += " — *" + " ".join(pens[:2]) + "*"
        evs, lieux = [], []
        for b in bloc:
            for e in b.get("evenements", []):
                if e["id"] not in evs:
                    evs.append(e["id"])
            if b["piece"] not in lieux:
                lieux.append(b["piece"])
        L.append(f"| {s['debut']}–{fin_h} | {', '.join(lieux)} | {s['titre']} | {txt.replace('|', '/')} | {', '.join(evs)} |")

    L += ["\n## Déplacements et lumière\n",
          f"- Entre les pièces (calculé sur le plan) : **{deplacements['entre_pieces_m']} m**, {deplacements['passages_de_piece']} passages de porte.",
          f"- Dans les pièces (estimé selon l'activité) : **{deplacements['dans_les_pieces_m_estimes']} m**.",
          f"- À l'extérieur : **{deplacements['exterieur_m']} m** (dénivelé +{deplacements['denivele_positif_m']} m / -{deplacements['denivele_negatif_m']} m).",
          f"- Escaliers : **{deplacements['marches_d_escalier']} marches**.",
          *([f"- En voiture : **{deplacements['voiture_m']} m**."] if deplacements.get("voiture_m") else []),
          f"- Total : **{deplacements['total_m']} m**, environ **{deplacements['foulees_et_marches']} foulées et marches**.",
          f"- Lumières allumées : **{st_['lumiere_allumages']} fois**.",
          "\nTrajets notables :\n"]
    for s in steps:
        d = s.get("deplacement")
        if d and (d.get("escalier") or d.get("parcours") or len(d.get("chemin", [])) > 3):
            parts = []
            if d.get("chemin"):
                parts.append(f"{' → '.join(d['chemin'])} ({d['distance_m']} m)")
            if d.get("escalier"):
                e = d["escalier"]
                parts.append(f"escalier en {e['sens']} : {e['marches']} marches en {e['duree_s']} s")
            for x in d.get("parcours", []):
                parts.append(f"{x['moyen']} {x['distance_m']} m" + (f" ({'+' if x['denivele_m'] > 0 else ''}{x['denivele_m']} m)" if x["denivele_m"] else ""))
            L.append(f"- {s['heure']} : " + " ; ".join(parts))

    L += ["\n## Émotions au fil de la journée (calculées)\n",
          "| Heure | Joie | Tristesse | Anxiété | Colère | Solitude | Fierté | Excitation | Concentration | Événements du pas |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for s in steps:
        if s.get("evenements") or s["heure"] in ("00:00", "12:00", "23:55"):
            if not s.get("evenements") and s["heure"] not in ("00:00", "12:00", "23:55"):
                continue
            e = s["emotions"]
            cause = ", ".join(x["id"] for x in s.get("evenements", [])) or "—"
            L.append(f"| {s['heure']} | {e['joie']:.2f} | {e['tristesse']:.2f} | {e['anxiete']:.2f} | {e['colere']:.2f} | {e['solitude']:.2f} | {e['fierte']:.2f} | {e['excitation']:.2f} | {e['concentration']:.2f} | {cause} |")

    L += ["\n## Besoins au fil de la journée\n",
          "| Heure | Faim | Soif | Énergie | Énergie ressentie | Hygiène | Toilettes | Social | Détente |", "|---|---|---|---|---|---|---|---|---|"]
    for h in ["00:00", "07:00", "09:00", "12:30", "14:00", "17:00", "19:00", "22:00", "23:55"]:
        b = steps[idx(h)]["besoins"]
        L.append(f"| {h} | {b['faim']} | {b['soif']} | {b['energie']} | {b['energie_ressentie']} | {b['hygiene']} | {b['toilettes']} | {b['social']} | {b['detente']} |")

    L += ["\n## Provisions\n", "| Produit | Consommé aujourd'hui | Reste |", "|---|---|---|"]
    for k, v in conso.items():
        pid = next((x for x in noms if noms[x]["produit"] == k), None)
        reste = etat_final["stock"].get(pid) if pid else None
        if v[1] is None:
            L.append(f"| {k} | utilisés | non suivis |")
        else:
            L.append(f"| {k} | {quantite(v[0], v[1])} | {'—' if reste is None else quantite(reste, v[1])} |")
    for k, v in prod.items():
        pid = next((x for x in noms if noms[x]["produit"] == k), None)
        L.append(f"| {k} (préparé : {quantite(v[0], v[1])}) | — | {quantite(etat_final['stock'].get(pid), v[1])} |")

    if magasin:
        M = magasin
        L += ["\n## Magasin\n",
              f"- Clients servis : **{M['clients']}** ; recette **{M['recette']:.2f} €** "
              f"(espèces {M['recette_especes']:.2f} €, carte {M['recette_carte']:.2f} €"
              + (f", à crédit sur l'ardoise {M['a_credit']:.2f} €" if M["a_credit"] else "") + ").",
              *([f"- Ruptures : {', '.join(M['ruptures'])}."] if M.get("ruptures") else []),
              "", "| Produit | Vendu | Livré | Repris | Prélevé | Stock en fin de journée |", "|---|---|---|---|---|---|"]
        for pid, l in M["produits"].items():
            if any(l[k] for k in ("vendu", "livre", "repris", "preleve")):
                L.append(f"| {l['nom']} | {l['vendu'] or ''} | {l['livre'] or ''} | {l['repris'] or ''} | {l['preleve'] or ''} | {l['stock']} |")
    if achats:
        L += ["\n## Achats\n", "| Produit | Quantité | Prix |", "|---|---|---|"]
        L += [f"| {k} | {quantite(v[0], v[1])} | {v[2]:.2f} € |" for k, v in achats.items()]
    if depenses:
        noms_comptes = {"especes": "espèces", "compte": "compte courant", "caisse": "caisse du magasin", "coffre": "coffre du magasin",
                        "ardoises": "ardoises des clients"}
        L.append("\nArgent : " + " ; ".join(f"{noms_comptes.get(c, c)} {m:+.2f} € (reste {etat_final['argent'].get(c, 0):.2f} €)"
                                            for c, m in depenses.items()) + ".")
    if perception:
        L += ["\n## Perception\n",
              f"- Pas éveillés où il remarque au moins un objet : **{perception['pas_avec_objets_vus']}** ; objets remarqués dans la journée : **{perception['objets_vus']}**.",
              "- Entendu : " + (", ".join(f"{k} ({v * 5} min)" for k, v in perception["entendu_pas"].items()) or "rien."),
              "- Remarques (écart entre ce qu'il croit et ce qu'il voit) : " + ("aucune." if not perception["remarques"] else "")]
        L += [f"  - {r}" for r in perception["remarques"]]
        if perception["a_son_insu"]:
            L.append("- À son insu :")
            L += [f"  - {r}" for r in perception["a_son_insu"]]
        fausses = perception["croyances_fausses_en_fin_de_journee"]
        L.append("- Croyances fausses en fin de journée : " + (", ".join(
            f"{k} (croit « {v} », en réalité « {etat_final['positions'].get(k)} »)" for k, v in fausses.items()) or "aucune."))
    L += ["\n## Bilan\n"] + [f"- {x}" for x in j.bilan]
    L.append(f"- **Endormissement** : {out['resume']['endormissement']}.")
    L.append("- **Écarts à la routine** :")
    L += [f"  - {e}" for e in j.ecarts]
    L.append("- **Besoins passés sous le seuil d'alerte (éveillé)** : " + (", ".join(alertes) if alertes else "aucun."))
    if alertes_sommeil:
        L.append("- **Pendant le sommeil** : " + ", ".join(f"{n} sous le seuil pendant {k * 5} minutes" for n, k in alertes_sommeil.items()) + ".")
    open(chemin_md, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return out
