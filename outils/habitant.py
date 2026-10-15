"""Habitant générique de Paradoxe : un seul moteur pour tous les habitants.

Un habitant est décrit par sa fiche : besoins, logement, et routines dont chaque
étape nomme une action du catalogue commun (data/monde/actions.json). Aucune
ligne de ce module n'est propre à un personnage.

À chaque pas, l'habitant donne un score aux actions possibles et fait la
meilleure :
- l'action de l'étape de routine en cours (l'ancrage) vaut 1 ;
- une action de réponse à un besoin (toilettes, soif, faim) vaut
  1 + (seuil − valeur) / seuil quand ce besoin passe sous son seuil d'alerte,
  sauf si l'ancrage le satisfait déjà, ne s'interrompt pas, ou finit dans les
  10 minutes ; elle dure un pas, puis l'ancrage reprend.
Les variantes d'une action se choisissent selon les besoins (sieste si
l'énergie est basse). Le moteur (moteur.py) calcule ensuite déplacements,
lumière, besoins et émotions, exactement comme pour les autres agents.

Les déplacements en véhicule se calculent avec la fiche (voiture : où il se
gare sur chaque site, distances entre sites) : il sort par la place de
stationnement du site de départ et rentre par celle du site d'arrivée. Un
événement que la fiche ne connaît pas n'a pas d'effet sur l'habitant.

La nuit s'enchaîne d'elle-même : l'étape « coucher » éteint, l'endormissement
dure selon l'anxiété et l'excitation, puis le sommeil va jusqu'à la première
étape du lendemain.

Objets : une action (ou une étape de routine) nomme les objets par leur rôle
(« lunettes », « cles », « tasse »…) ; la fiche dit quel objet tient ce rôle et
où il se trouve dans chaque état (« porte », « usage »… ; « rangement » est sa
place de départ). « objets » le déplace au premier pas de l'action ; « tient »
le garde pendant toute l'action et le repose dès que le pas suivant ne le
demande plus (il pose ses lunettes pour aller aux toilettes). Chaque geste part
de là où il croit l'objet ; s'il n'y est pas, il fait sans.

Provisions : un repas consomme le menu de la fiche (menus_prevus : ingrédients
au début de la préparation ; plat préparé et portion au début du repas
proprement dit) ; une collation ou un café, ce que la fiche prévoit pour cet
usage (collations), en alternant les choix d'un jour à l'autre. Il n'utilise
que ce qu'il a ; ce qui manque est noté dans les écarts.
"""
import datetime

from agent import JOURS, phase_sommeil
from moteur import PAS_PAR_JOUR, Journee, Simulation, hm, idx, position_initiale


class Habitant:
    def __init__(self, fiche, catalogue, date, etat):
        self.fiche = fiche
        self.A = catalogue["actions"]
        self.date = date
        self.jour = JOURS[datetime.date.fromisoformat(date).weekday()]
        self.sim = Simulation(fiche, date, etat)
        self.PIECES = fiche["domicile"]["pieces"]
        self.SEUILS = {n: b["seuil_alerte"] for n, b in fiche["besoins"].items()}
        self.EV = set(fiche["modele_emotionnel"]["evenements"])
        self.SITE = {pc["id"]: pc.get("lieu") for pc in self.PIECES}
        self.LIEU_DU_SITE = fiche["domicile"]["plan"].get("lieux_des_sites", {})
        self.ACCES = fiche["domicile"]["plan"].get("acces", {})
        self.VEHICULE = fiche.get("voiture") or {}
        self.site = self.SITE.get(self.sim.piece)
        self.trajet = None       # trajet en véhicule en cours : site d'arrivée et distance par pas
        self.BESOINS = {a["besoin"]: aid for aid, a in self.A.items() if a.get("besoin")}
        self.etapes = self.etapes_du_jour(self.jour)
        self.mem = dict(etat.get("habitant") or {"endormi_a": self.endormissement_veille()})
        self.j = Journee(date, self.jour, extinction="23:00")
        self.j.methode = [
            "Généré par l'habitant générique (outils/habitant.py) : routines de la fiche, catalogue d'actions commun (data/monde/actions.json), choix par l'utilité.",
            "Calculé par outils/moteur.py avec les règles de la fiche : déplacements, lumière, besoins, émotions et concentration.",
            "La journée part de l'état exact de la fin de la veille.",
        ]
        self.decisions = []
        self.allumes = set(etat.get("appareils", []))
        self.faits = set()       # premiers pas déjà faits : (début d'étape, phase)
        self.coucher = None      # (pas d'extinction, pas d'endormissement)
        self.attente = None      # pas décidé, pas encore calculé : (st, s, titre, routine, suite)
        self.action_courante = {}  # action du catalogue du pas décidé
        self.journal = []          # action du catalogue de chaque pas calculé
        self.etape_courante = None
        self.opportunites = {}   # début d'étape -> besoins satisfaits en s'y mettant
        self.ROLES = {o["role"]: o for o in fiche["objets"] if o.get("role")}
        self.MENUS = fiche.get("menus_prevus") or {}
        self.COLLATIONS = fiche.get("collations") or {}
        self.tenus = {}          # rôle -> état des objets gardés pendant l'action en cours
        self.collations_du_jour = 0

    # ------------------------------------------------------------ fiche
    def etapes_du_jour(self, jour):
        out = []
        for r in self.fiche["habitudes"]["routines"]:
            if jour in r["jours"]:
                for e in r["etapes"]:
                    out.append((idx(e["debut"]), idx(e["fin"]) if e["fin"] else PAS_PAR_JOUR, e, r["id"]))
        return sorted(out, key=lambda x: x[0])

    def endormissement_veille(self):
        """Premier jour : endormi la veille à l'heure de son coucher, après un endormissement normal."""
        veille = JOURS[(JOURS.index(self.jour) - 1) % 7]
        c = next((d for d, f, e, r in self.etapes_du_jour(veille) if e["activite"] == "coucher"), idx("23:00"))
        return c + self.fiche["sante"]["sommeil"]["endormissement_minutes_normal"] // 5 - PAS_PAR_JOUR

    def piece_pour(self, mot, meme_site=False):
        """Pièce dont l'identifiant, le nom ou le mobilier contient le mot, de préférence sur le site où il se trouve
        (seulement sur ce site si meme_site)."""
        m = mot.lower()
        trouvees = [pc["id"] for pc in self.PIECES
                    if m in pc["id"].split("-") or m in pc["nom"].lower() or any(m in x.lower() for x in pc["mobilier"])]
        ici = [p for p in trouvees if self.SITE.get(p) == getattr(self, "site", None)]
        return (ici or ([] if meme_site else trouvees) or [None])[0]

    @property
    def i(self):
        return len(self.sim.steps)

    # ------------------------------------------------------------ décision
    def etape(self, i):
        return next(((d, f, e, r) for d, f, e, r in self.etapes if d <= i < f), None)

    def resoudre(self, d, f, e, i):
        """Action de l'étape au pas i : phase en cours et variantes selon les besoins."""
        a = dict(self.A[e["activite"]])
        # besoins que l'action satisfait, toutes phases comprises (pas de fruit juste avant le repas)
        a["satisfait"] = set(a.get("effets", {})) | {b for ph in a.get("phases", []) for b in ph.get("effets", {})}
        phase, debut = 0, d
        if a.get("phases"):
            n, cumul = f - d, 0.0
            for k, ph in enumerate(a["phases"]):
                fin_ph = d + round(n * (cumul + ph["part"]))
                if i < fin_ph or k == len(a["phases"]) - 1:
                    a.update({x: v for x, v in ph.items() if x not in ("part", "lieu")})
                    if "lieu" in ph:
                        a["lieu_phase"] = ph["lieu"]
                    phase, debut = k, d + round(n * cumul)
                    break
                cumul += ph["part"]
            for x in ("effets", "ev"):
                if x not in a["phases"][phase]:
                    a.pop(x, None)
        for v in a.get("variantes", []):
            if all(self.sim.besoins[b] < s for b, s in v["si_besoin_sous"].items()):
                a.update({x: y for x, y in v.items() if x != "si_besoin_sous"})
        # objets propres à l'étape (la fiche les ajoute à ceux de l'action)
        for x in ("objets", "tient"):
            if x in e:
                a[x] = {**self.etats(a.get(x)), **self.etats(e[x])}
        if "consomme" in e:
            a["consomme"] = a.get("consomme", []) + e["consomme"]
        a["vivres"] = self.menu_du_pas(a, e, d, phase)
        return a, (d, phase), debut

    # ------------------------------------------------------------ objets
    @staticmethod
    def etats(x):
        """Rôles d'objets et état voulu ; une simple liste de rôles veut dire « porté »."""
        return {r: "porte" for r in x} if isinstance(x, list) else dict(x or {})

    def position(self, o, etat):
        if etat == "rangement":
            return o.get("positions", {}).get("rangement") or position_initiale(o)
        return o.get("positions", {}).get(etat) or {"porte": "dans sa main"}.get(etat)

    def gestes(self, a, premier):
        """Déplacements d'objets du pas : ceux de l'action au premier pas, ceux qu'elle garde en main, et ceux qu'il
        tenait et que ce pas ne demande plus (reposés à leur place). Chaque geste part de là où il croit l'objet."""
        tient = self.etats(a.get("tient"))
        voulus = {r: "rangement" for r in self.tenus if r not in tient}
        if premier:
            voulus.update(self.etats(a.get("objets")))
        voulus.update(tient)
        self.tenus = {r: e for r, e in tient.items() if r in self.ROLES}
        out = []
        for role, etat in voulus.items():
            o = self.ROLES.get(role)
            vers = self.position(o, etat) if o else None
            if vers is None:
                continue
            de = self.sim.croyances.get(o["id"])
            if de == vers:
                continue
            if self.sim.positions.get(o["id"]) != de:
                self.decisions.append(f"{hm(self.i)} : {o['nom']} n'est pas là où il le croyait ({de}) ; fait sans.")
                self.tenus.pop(role, None)
                continue
            out.append({"objet": o["id"], "de": de, "vers": vers})
        return out

    # ------------------------------------------------------------ provisions
    def menu_du_pas(self, a, e, d, phase):
        """Ce que le repas de l'étape consomme et prépare à cette phase : ingrédients au début de la préparation ;
        plat préparé et portion au début du repas proprement dit (dernière phase). Le repas se lit dans la fiche
        (menus_prevus, menu du jour puis menu de tous les jours) : celui que nomme l'étape (« repas »), sinon
        celui que nomme l'action, sinon le déjeuner avant 16:00 (ou le brunch) et le dîner après."""
        moment = e.get("repas") or a.get("menu")
        if not moment:
            return None
        if moment is True:
            moment = "dejeuner" if d < idx("16:00") else "diner"
        jour = self.MENUS.get(self.jour) or {}
        m = jour.get(moment) or self.MENUS.get(moment) or (jour.get("brunch") if moment == "dejeuner" else None)
        if not isinstance(m, dict):
            return None
        derniere = phase == max(0, len(a.get("phases", [])) - 1)
        return {"plat": m.get("plat", moment),
                "ingredients": m.get("ingredients", []) if phase == 0 else [],
                "prepare": m.get("prepare", []) if derniere else [],
                "portion": m.get("portion", []) if derniere else []}

    def disponibles(self, conso, prod=()):
        """Ce qui peut être consommé avec le stock (et ce qui vient d'être préparé), et ce qui manque."""
        P, dispo = self.sim.PRODUITS, dict(self.sim.stock)
        for pid, q in prod:
            dispo[pid] = dispo.get(pid, 0) + q
        ok, manque = [], []
        for pid, q in conso:
            spec = P.get(pid)
            if spec is None or (spec.get("suivi", True) and dispo.get(pid, 0) < q):
                manque.append(spec["produit"] if spec else pid)
                continue
            if spec.get("suivi", True):
                dispo[pid] -= q
            ok.append({"produit": pid, "quantite": q})
        return ok, manque

    def provisions(self, a, st):
        """Au premier pas : consommation et production du repas, puis ce que l'action prend pour un usage
        (café, collation), en alternant les choix possibles ; une collation impossible ne nourrit pas."""
        prod, conso, manque = [], [], []
        v = a.get("vivres")
        if v:
            prod = [{"produit": p, "quantite": q} for p, q in v["prepare"] if p in self.sim.PRODUITS]
            conso, manque = self.disponibles(v["ingredients"] + v["portion"], [(x["produit"], x["quantite"]) for x in prod])
            if manque:
                self.decisions.append(f"{hm(self.i)} : {v['plat']} sans {', '.join(manque)} (plus en stock).")
        for usage in a.get("consomme", []):
            choix = self.COLLATIONS.get(usage)
            if not choix:
                continue
            possibles = [c for c in choix if not self.disponibles(c.items())[1]]
            if possibles:
                c = possibles[(datetime.date.fromisoformat(self.date).weekday() + self.collations_du_jour) % len(possibles)]
                self.collations_du_jour += 1
                conso += self.disponibles(c.items())[0]
                break
        else:
            if a.get("consomme") and any(u in self.COLLATIONS for u in a["consomme"]):
                self.decisions.append(f"{hm(self.i)} : plus rien pour « {a['texte']} ».")
                if "faim" in st.get("effets", {}):
                    del st["effets"]["faim"]
        if prod:
            st["production"] = prod
        if conso:
            st["consommation"] = conso

    def utilite(self, a, d, f, i):
        """Scores des actions possibles : l'ancrage vaut 1 ; un besoin pressant (sous son seuil d'alerte) peut
        l'emporter à tout moment ; au début d'une étape, un besoin simplement inconfortable (sous le double de
        son seuil) aussi, avec un score moindre : il en profite avant de s'y mettre."""
        scores = [(1.0, None)]
        if a.get("ininterrompable") or f - i <= 2 or self.sim.piece not in self.sim.graph:
            return scores
        transition = i == d + self.opportunites.get(d, 0)
        for besoin, aid in self.BESOINS.items():
            v, s = self.sim.besoins[besoin], self.SEUILS[besoin]
            if besoin in a.get("satisfait", ()) or self.piece_pour(self.A[aid]["lieu"], meme_site=True) is None:
                continue
            if v < s:
                scores.append((1 + (s - v) / s, aid))
            elif transition and v < 2 * s:
                scores.append((1 + 0.5 * (2 * s - v) / (2 * s), aid))
        return sorted(scores, key=lambda x: -x[0])

    # ------------------------------------------------------------ émission
    def emettre(self, a, titre, routine, piece, premier, avec=(), garder_appareils=False, lieu="domicile", extra=None):
        self.action_courante = a
        st = {"action": a["texte"], "pensee": None, "piece": piece, "lieu": lieu, "mode": a.get("mode", "eveille"),
              "charge": a.get("charge", "simple"), "posture": a.get("posture", "debout")}
        st.update(extra or {})
        if premier:
            if a.get("effets"):
                st["effets"] = dict(a["effets"])
            evs = [e for e in a.get("ev", []) + a.get("ev_si_seul", []) if e in self.EV]
            if evs:
                st["ev"] = evs
            self.provisions(a, st)
        objets = self.gestes(a, premier)
        if objets:
            st["objets"] = objets
        voulus = set(self.allumes) if garder_appareils else set(a.get("appareils", [])) | set(avec)
        app = {"allume": sorted(voulus - self.allumes), "eteint": sorted(self.allumes - voulus)}
        if premier:
            app["allume"] += [x.replace("{piece}", piece) for x in a.get("allume", [])]
            app["eteint"] += [x.replace("{piece}", piece) for x in a.get("eteint", [])]
        if self.SITE.get(self.sim.piece) is not None and self.SITE.get(piece) != self.SITE.get(self.sim.piece):
            # il quitte le site : il éteint tout derrière lui
            app["eteint"] += [f"lumiere-{p}" for p, v in self.sim.lumieres.items() if v and self.sim.eclairage_auto(p)] + sorted(self.allumes)
            voulus = set()
        if a.get("lumiere") and piece in self.sim.PIECES and self.sim.besoin_lumiere(piece, self.i) and not self.sim.lumieres.get(piece):
            app["allume"].append(f"lumiere-{piece}")
        if app["allume"] or app["eteint"]:
            st["app"] = app
        self.allumes = voulus
        if "radio" in voulus:
            st["radio"] = True
        if "lecteur-cd" in voulus:
            st["musique"] = True
        if "television" in voulus:
            st["tele"] = a.get("tele", True)
        self.pousser(st, titre, routine)
        return st

    def pousser(self, st, titre, routine, suite=None):
        """Le pas est décidé ; il sera calculé par executer(), après que le quartier y a ajouté les rencontres."""
        s = {"titre": titre, "routine": routine, "piece": st.pop("piece"), "lieu": st.pop("lieu"), "mode": st.pop("mode"),
             "charge": st.pop("charge"), "posture": st.pop("posture")}
        self.attente = (st, s, titre, routine, suite)

    def executer(self):
        st, s, titre, routine, suite = self.attente
        self.attente = None
        entree = self.sim.pas(st, s)
        self.journal.append(self.action_courante)
        segs = self.j.segments
        if segs and segs[-1]["titre"] == titre and segs[-1]["routine"] == routine:
            segs[-1]["pas"].append(st)
        else:
            segs.append({"debut": hm(entree["pas"]), "titre": titre, "routine": routine, "pas": [st]})
        if suite:
            suite(entree)
        return entree

    def dormir(self, titre):
        lit = self.piece_pour(self.A["sommeil"]["lieu"])
        a = self.A["sommeil"]
        endormi_a = self.coucher[1] if self.coucher else self.mem["endormi_a"]
        phase = phase_sommeil((self.i - endormi_a) * 5)
        st = {"action": a["texte"] if phase != "micro-éveil" else "Se retourne et se rendort.", "pensee": None, "piece": lit,
              "lieu": "domicile", "mode": "sommeil", "charge": "sommeil", "posture": "allongé", "phase_sommeil": phase}
        if self.allumes:
            st["app"] = {"eteint": sorted(self.allumes)}
            self.allumes = set()
        objets = self.gestes({}, False)
        if objets:
            st["objets"] = objets
        self.pousser(st, titre, "sommeil")

    # ------------------------------------------------------------ journée
    def vivre(self):
        while self.i < PAS_PAR_JOUR:
            self.decider()
            self.executer()
        return self.terminer()

    def decider(self):
        """Décide le pas en cours (sans le calculer)."""
        veille = JOURS[(JOURS.index(self.jour) - 1) % 7]
        i = self.i
        self.etape_courante = None
        self.action_courante = {}
        if self.coucher:
            if i >= self.coucher[1]:
                self.dormir("Sommeil")
            else:
                lit = self.piece_pour(self.A["coucher"]["lieu"])
                self.pousser({"action": "Cherche le sommeil.", "pensee": None, "piece": lit, "lieu": "domicile", "mode": "eveille",
                              "charge": "repos", "posture": "allongé"}, "Endormissement", self.routine_coucher)
            return
        et = self.etape(i)
        if et is None:
            self.dormir(f"Nuit de {veille} à {self.jour}")
            return
        self.etape_courante = et
        d, f, e, r = et
        a, cle, debut = self.resoudre(d, f, e, i)
        if a.get("sommeil"):
            self.endormir(a, e, r)
            return
        if a.get("mode") == "sommeil":
            self.dormir(e["action"])
            return
        score, besoin = self.utilite(a, d, f, i)[0]
        if besoin:
            b = self.A[besoin]
            piece = self.piece_pour(b["lieu"], meme_site=True)
            v = round(self.sim.besoins[b["besoin"]], 1)
            if v < self.SEUILS[b["besoin"]]:
                self.decisions.append(f"{hm(i)} : {b['besoin']} sous le seuil d'alerte ({v}, score {round(score, 2)}) ; interrompt « {e['action']} ».")
                self.emettre(b, "Besoin pressant", "interruption", piece, True, garder_appareils=True)
            else:
                self.opportunites[d] = self.opportunites.get(d, 0) + 1
                self.emettre(dict(b, texte=b["texte"].replace("S'interrompt pour", "Avant de s'y mettre,")), e["action"], r, piece, True,
                             garder_appareils=True)
            return
        lieu, extra = "domicile", {}
        if a.get("vehicule"):
            piece, lieu, extra = self.VEHICULE.get("nom_court", "véhicule"), e["lieu"], self.conduire(d, f, i)
        elif a.get("exterieur"):
            piece, lieu = e["lieu"], "exterieur"
        elif a.get("lieu_phase"):
            piece = self.piece_pour(a["lieu_phase"]) or e["lieu"]
        elif e["lieu"] in self.sim.graph:
            piece = e["lieu"]
        else:
            piece = self.piece_pour(a["lieu"]) or self.sim.piece
        if lieu == "domicile":
            lieu = self.LIEU_DU_SITE.get(self.SITE.get(piece), "domicile")
        if self.trajet and not a.get("vehicule"):
            # arrivée : il rentre par la place de stationnement du site où il arrive
            parking = self.VEHICULE.get("stationnements", {}).get(self.SITE.get(piece))
            if parking and parking in self.sim.graph and lieu != "exterieur":
                extra["retour"] = parking
            self.trajet = None
        # à pied : il sort par l'accès de son site (la rue) et entre par celui du site où il arrive
        depuis, vers, G = self.SITE.get(self.sim.piece), self.SITE.get(piece), self.sim.graph
        if depuis and vers != depuis and "sortie" not in extra and not a.get("vehicule"):
            if vers is None and piece not in G and self.ACCES.get(depuis) in G:
                extra["sortie"] = self.ACCES[depuis]
            elif vers and self.ACCES.get(vers) in G:
                extra["retour"] = self.ACCES[vers]
        elif vers and not depuis and "retour" not in extra and self.sim.piece not in G and self.ACCES.get(vers) in G:
            extra["retour"] = self.ACCES[vers]
        if piece in self.SITE and self.SITE[piece]:
            self.site = self.SITE[piece]
        premier = cle not in self.faits
        self.faits.add(cle)
        self.emettre(a, e["action"], r, piece, premier, avec=e.get("avec", ()), lieu=lieu, extra=extra)

    def conduire(self, d, f, i):
        """Un pas en véhicule : au premier, il sort par la place de stationnement du site ; la distance de
        l'itinéraire entre les deux sites (fiche, voiture.itineraires) se répartit sur les pas du trajet."""
        V = self.VEHICULE
        if i == d or self.trajet is None:
            suivante = next((e for d2, f2, e, r in self.etapes if d2 >= f), None)
            arrivee = self.SITE.get(suivante["lieu"]) if suivante else None
            it = next((x for x in V.get("itineraires", []) if set(x["entre"]) == {self.site, arrivee}), None)
            self.trajet = {"arrivee": arrivee, "par_pas": round(it["distance_m"] / (f - d)) if it else 0}
            parking = V.get("stationnements", {}).get(self.site)
            extra = {"sortie": parking} if parking in self.sim.graph and parking not in self.SITE else {}
        else:
            extra = {}
        if self.trajet["par_pas"]:
            extra["parcours"] = [{"moyen": "voiture", "distance_m": self.trajet["par_pas"], "denivele_m": 0}]
        return extra

    def endormir(self, a, e, r):
        """Étape du coucher : il éteint ; l'endormissement dure selon son état ; puis il dort jusqu'au lendemain."""
        lit = self.piece_pour(a["lieu"])
        st = {"action": a["texte"], "pensee": None, "piece": lit, "lieu": "domicile", "mode": "eveille", "charge": "repos", "posture": "allongé"}
        st["app"] = {"eteint": sorted(self.allumes) + [f"lumiere-{lit}"]}
        self.allumes = set()
        objets = self.gestes(a, True)
        if objets:
            st["objets"] = objets
        self.routine_coucher = r

        def apres_extinction(entree):
            latence = self.sim.latence_endormissement(entree["emotions"])
            self.j.extinction, self.j.endormissement = entree["heure"], latence
            self.coucher = (entree["pas"], entree["pas"] + latence // 5)
            self.mem["endormi_a"] = self.coucher[1] - PAS_PAR_JOUR
        self.pousser(st, e["action"], r, suite=apres_extinction)

    def terminer(self):
        etat_final, stats = self.sim.terminer(self.j.extinction, self.j.endormissement)
        etat_final["habitant"] = self.mem
        self.j.ecarts = self.decisions
        self.j.bilan = ["Journée vécue par l'habitant générique."]
        return self.sim.steps, etat_final, stats
