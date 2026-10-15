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
import math

from agent import JOURS, phase_sommeil
from clientele import Comptoir, libelle
from moteur import PAS_PAR_JOUR, Journee, Simulation, hm, idx, position_initiale

COMMERCES = {}   # commerces des autres habitants, lus une fois


class Habitant:
    def __init__(self, fiche, catalogue, date, etat, perturbations=None):
        self.fiche = fiche
        self.A = catalogue["actions"]
        self.date = date
        self.jour = JOURS[datetime.date.fromisoformat(date).weekday()]
        self.sim = Simulation(fiche, date, etat, perturbations)
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
        self.APPRO = fiche.get("approvisionnement") or {}
        self.COMMERCE = self.commerce(self.APPRO["commerce"]) if self.APPRO else {}
        self.listes = {}         # début d'une étape de courses -> liste établie en partant (None : il n'y va pas)
        self.comptoir = None     # service au comptoir de son propre commerce, créé au premier client
        self.achat = None        # achat du pas décidé dans le commerce d'un autre habitant
        self.retenues = []       # plages (début, fin) où quelqu'un l'a retenu (voyageur.py)
        self.imposes = {}        # pas -> (texte, pièce, titre) : ce qu'une réaction lui fait faire (voyageur.py)

    def commerce(self, pid):
        """Le commerce où il s'approvisionne : celui de sa propre fiche (il prélève), ou celui d'un autre habitant (il achète)."""
        if pid == self.fiche["meta"].get("id"):
            return self.fiche["commerce"]
        if pid not in COMMERCES:
            from fiches import charger
            COMMERCES[pid] = charger(pid)["commerce"]
        return COMMERCES[pid]

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

    def lieu_de(self, piece):
        """Le lieu d'une pièce : celui de son site (sa maison, sa boutique, le logement où il est en visite) ; une pièce
        hors plan (le jardin) est dans le lieu du site où il se trouve."""
        site = self.SITE.get(piece) or (self.site if piece in self.sim.graph else None)
        return self.LIEU_DU_SITE.get(site, "domicile")

    @property
    def i(self):
        return len(self.sim.steps)

    # ------------------------------------------------------------ décision
    def etape(self, i):
        """Étape en cours ; si deux étapes se recouvrent, la plus courte l'emporte (des courses prises sur le temps libre).
        Des courses qui n'ont pas lieu (commerce fermé, rien ne manque) rendent la place à l'étape qu'elles recouvrent."""
        en_cours = [(d, f, e, r) for d, f, e, r in self.etapes if d <= i < f and not self.sans_courses(d, e)]
        return min(en_cours, key=lambda x: x[1] - x[0]) if en_cours else None

    def resoudre(self, d, f, e, i):
        """Action de l'étape au pas i : phase en cours et variantes selon les besoins."""
        a = dict(self.A[e["activite"]])
        # besoins que l'action satisfait, toutes phases comprises (pas de fruit juste avant le repas)
        a["satisfait"] = set(a.get("effets", {})) | {b for ph in a.get("phases", []) for b in ph.get("effets", {})}
        phase, debut = 0, d
        a["duree_phase"] = f - d
        if a.get("phases"):
            n, cumul = f - d, 0.0
            for k, ph in enumerate(a["phases"]):
                fin_ph = d + round(n * (cumul + ph["part"]))
                if i < fin_ph or k == len(a["phases"]) - 1:
                    a.update({x: v for x, v in ph.items() if x not in ("part", "lieu")})
                    if "lieu" in ph:
                        a["lieu_phase"] = ph["lieu"]
                    phase, debut = k, d + round(n * cumul)
                    a["duree_phase"] = max(1, fin_ph - debut)
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
        if e.get("approvisionne"):
            a["approvisionne"] = True
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
        # un état que la fiche ne décrit pas pour cet objet : porté sur lui
        return o.get("positions", {}).get(etat) or o.get("positions", {}).get("porte") or "dans sa main"

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
                self.decisions.append(f"{hm(self.i)} : {o['nom']} : " + (f"n'est pas là où il le croyait ({de})" if de else "il ne sait plus où il est")
                                      + " ; fait sans.")
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
        m = self.menu(self.jour, a, e, d)
        if m is None:
            return None
        moment = m.get("plat")
        derniere = phase == max(0, len(a.get("phases", [])) - 1)
        return {"plat": m.get("plat", moment),
                "ingredients": m.get("ingredients", []) if phase == 0 else [],
                "prepare": m.get("prepare", []) if derniere else [],
                "portion": m.get("portion", []) if derniere else []}

    def menu(self, jour, a, e, d):
        """Le repas de la fiche que sert l'étape (début d), ou None."""
        moment = e.get("repas") or a.get("menu")
        if not moment:
            return None
        if moment is True:
            moment = "dejeuner" if d < idx("16:00") else "diner"
        menus = self.MENUS.get(jour) or {}
        m = menus.get(moment) or self.MENUS.get(moment) or (menus.get("brunch") if moment == "dejeuner" else None)
        return m if isinstance(m, dict) else None

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

    # ------------------------------------------------------------ approvisionnement
    def approvisionne(self, e):
        return bool(e.get("approvisionne") or self.A[e["activite"]].get("courses"))

    def sans_courses(self, d, e):
        """Des courses (action « courses ») n'ont pas lieu si le commerce est fermé ou si rien ne manque ; décidé une fois,
        en partant."""
        if not self.A[e["activite"]].get("courses"):
            return False
        if d not in self.listes and any(a <= d < b for a, b in self.retenues):
            self.decisions.append(f"{hm(self.i)} : retenu à l'heure de partir, il renonce aux courses.")
            self.listes[d] = None
        if d not in self.listes:
            ouvert = any(idx(a) <= d and d + 6 <= idx(b) for a, b in self.COMMERCE.get("horaires", {}).get(self.jour, []))
            lignes = self.liste_de_courses(d) if ouvert else []
            if not ouvert:
                self.decisions.append(f"{hm(d)} : {self.COMMERCE.get('nom', 'le commerce')} est fermé à cette heure ; pas de courses.")
            elif not lignes:
                self.decisions.append(f"{hm(d)} : rien ne manque ; pas de courses.")
            self.listes[d] = lignes or None
        return self.listes[d] is None

    def besoins_repas(self, depuis):
        """Ce que demandent les repas de la fiche (menus_prevus) d'ici au prochain approvisionnement prévu par ses
        routines (au plus tard la fin de la semaine)."""
        j0 = JOURS.index(self.jour)
        fin = (7, 0)
        for k in range(j0, 7):
            fin = next(((k, d) for d, f, e, r in self.etapes_du_jour(JOURS[k]) if (k, d) > (j0, depuis) and self.approvisionne(e)), fin)
            if fin != (7, 0):
                break
        besoin = {}
        for k in range(j0, min(fin[0], 6) + 1):
            for d, f, e, r in self.etapes_du_jour(JOURS[k]):
                m = self.menu(JOURS[k], self.A[e["activite"]], e, d) if (j0, depuis) < (k, d) < fin else None
                for pid, q in (m or {}).get("ingredients", []) + (m or {}).get("portion", []):
                    besoin[pid] = besoin.get(pid, 0) + q
        return besoin

    def liste_de_courses(self, depuis):
        """Ce qu'il rapporte du commerce : ce qui est sous sa cible ou son seuil (approvisionnement.liste), ce que demandent
        ses repas d'ici au prochain approvisionnement, et les envies du jour. Chaque provision se trouve au catalogue sous
        son identifiant (ou celui que donne « magasin »), « par_unite » de la provision (ou « quantite » du catalogue) par
        unité vendue."""
        A, P = self.APPRO, self.sim.PRODUITS
        cat = {c["produit"]: c for c in self.COMMERCE.get("catalogue", [])}
        lignes = {}
        def unite(pid):
            spec = P.get(pid)
            c = cat.get(spec.get("magasin", pid)) if spec else None
            return (c, spec.get("par_unite") or c["quantite"]) if c else (None, None)
        de_cote = {x["produit"] for x in A.get("mis_de_cote", [])}   # ceux-là, il les met de côté à la livraison
        def ajouter(pid, n):
            c, u = unite(pid)
            if c and n > 0 and pid not in de_cote:
                x = lignes.setdefault(pid, {"maison": pid, "c": c, "u": u, "n": 0})
                x["n"] += n
        stock = lambda pid: self.sim.stock.get(pid, 0) + (lignes[pid]["n"] * lignes[pid]["u"] if pid in lignes else 0)
        for l in A.get("liste", []):
            c, u = unite(l["produit"])
            if not c:
                continue
            if "cible" in l:
                manque = l["cible"] - stock(l["produit"])
                if manque >= l.get("minimum", 1):
                    ajouter(l["produit"], math.ceil(manque / u))
            elif stock(l["produit"]) < l["seuil"]:
                ajouter(l["produit"], max(1, math.ceil(l["achat"] / u)))
        for pid, q in self.besoins_repas(depuis).items():
            c, u = unite(pid)
            if c and P[pid].get("suivi", True) and q > stock(pid):
                ajouter(pid, math.ceil((q - stock(pid)) / u))
        for x in A.get("envies", []):
            if x["jour"] == self.jour:
                ajouter(x["produit"], x["unites"])
        return list(lignes.values())

    @staticmethod
    def libelle(x):
        nom = x["c"]["nom"].split(" (")[0]
        return nom if x["n"] == 1 else f"{x['n']} × {nom}"

    def approvisionner(self, st):
        """Au commerce : il achète sa liste et paie (espèces sous un montant, s'il lui en reste assez, sinon carte) ;
        dans son propre commerce, il la prélève sur le stock du magasin, dans la limite de ce qui reste."""
        d = self.etape_courante[0] if self.etape_courante else self.i
        lignes = self.listes.get(d) or self.liste_de_courses(self.i)
        if not lignes:
            return
        if self.COMMERCE is self.fiche.get("commerce"):
            pris, textes, manques, reste = [], [], [], dict(self.sim.boutique)
            for x in lignes:
                cid = x["c"]["produit"]
                n = min(x["n"], reste.get(cid, 0))
                reste[cid] = reste.get(cid, 0) - n
                if n < x["n"]:
                    manques.append(x["c"]["nom"].split(" (")[0])
                if n > 0:
                    pris.append({"produit": cid, "quantite": n, "maison": x["maison"], "quantite_maison": n * x["u"]})
                    textes.append(self.libelle(dict(x, n=n)))
            if pris:
                st["prelevements"] = pris
            self.decisions.append(f"{hm(self.i)} : prend au magasin pour la maison : {', '.join(textes) or 'rien'}"
                                  + (f" ; plus de {', '.join(manques)} en rayon." if manques else "."))
            return
        achats = [{"produit": x["maison"], "quantite": x["n"] * x["u"], "prix": round(x["n"] * x["c"]["prix"], 2)} for x in lignes]
        total = round(sum(x["prix"] for x in achats), 2)
        P = self.APPRO.get("paiement", {})
        especes = total <= P.get("especes_si_moins_de", 0) and self.sim.argent.get("especes", 0) - total >= P.get("garde_en_especes", 0)
        st["achats"] = achats
        st["argent"] = {"especes" if especes else "compte": -total}
        # ce que le commerçant lui vend, s'il vit dans le même quartier (quartier.py)
        self.achat = {"commerce": self.APPRO["commerce"], "lignes": lignes, "paiement": "especes" if especes else "carte"}
        self.decisions.append(f"{hm(self.i)} : courses : {', '.join(self.libelle(x) for x in lignes)} "
                              f"({f'{total:.2f}'.replace('.', ',')} €, {'en espèces' if especes else 'par carte'}).")

    def fatigue(self, a, i):
        """Le soir (après 21:00), épuisé (énergie sous son seuil d'alerte) pendant une détente qui ne le captive pas
        (télévision, lecture, temps libre, et non un match, une partie ou un film), il va se coucher sans attendre l'heure."""
        if "energie" not in self.SEUILS or i < idx("21:00") or self.sim.besoins["energie"] >= self.SEUILS["energie"]:
            return False
        if a.get("captivant") or a.get("mode") not in ("loisir", "lecture", "sieste") or self.sim.piece not in self.sim.graph:
            return False
        coucher = next(((d, f, e, r) for d, f, e, r in self.etapes if d > i and e["activite"] == "coucher"), None)
        if not coucher:
            return False
        d, f, e, r = coucher
        self.decisions.append(f"{hm(i)} : épuisé (énergie {round(self.sim.besoins['energie'], 1)}), il va se coucher sans attendre {e['debut']}.")
        a_c, _, _ = self.resoudre(d, f, e, i)
        self.endormir(a_c, e, r)
        return True

    def utilite(self, a, d, f, i):
        """Scores des actions possibles : l'ancrage vaut 1 ; un besoin pressant (sous son seuil d'alerte) peut
        l'emporter à tout moment ; au début d'une étape, un besoin simplement inconfortable (sous le double de
        son seuil) aussi, avec un score moindre : il en profite avant de s'y mettre. Avant une action qui anticipe
        (une sortie qu'il ne peut pas interrompre), il répond à un besoin qui passerait sous son seuil avant la fin."""
        scores = [(1.0, None)]
        if self.sim.piece not in self.sim.graph:
            # dehors : seulement dans un lieu public qui a ses commodités (cinéma, bureau), pour un besoin pressant
            for besoin, aid in self.BESOINS.items():
                v, s = self.sim.besoins[besoin], self.SEUILS[besoin]
                if besoin in a.get("commodites", ()) and v < s and f - i > 2:
                    scores.append((1 + (s - v) / s, aid))
            return sorted(scores, key=lambda x: -x[0])
        transition = i == d + self.opportunites.get(d, 0)
        anticipe = transition and a.get("anticipe")
        if not anticipe and (a.get("ininterrompable") or f - i <= 2):
            return scores
        for besoin, aid in self.BESOINS.items():
            v, s = self.sim.besoins[besoin], self.SEUILS[besoin]
            if besoin in a.get("satisfait", ()) or self.piece_pour(self.A[aid]["lieu"], meme_site=True) is None:
                continue
            if anticipe:
                prevu = v + self.fiche["besoins"][besoin]["variation_par_pas"]["eveille"] * (f - i)
                if prevu < s:
                    scores.append((1 + (s - prevu) / s, aid))
            elif v < s:
                scores.append((1 + (s - v) / s, aid))
            elif transition and v < 2 * s:
                scores.append((1 + 0.5 * (2 * s - v) / (2 * s), aid))
        return sorted(scores, key=lambda x: -x[0])

    # ------------------------------------------------------------ émission
    def emettre(self, a, titre, routine, piece, premier, avec=(), garder_appareils=False, lieu="domicile", extra=None):
        self.action_courante = a
        if lieu == "domicile":
            lieu = self.lieu_de(piece)   # une interruption à la boutique est à la boutique, une nuit chez soi dans son logement
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
            if a.get("approvisionne"):
                self.approvisionner(st)
            if a.get("livraison"):
                self.livrer(st)
            if a.get("caisse_au_coffre"):
                self.caisse_au_coffre(st)
            if a.get("depot_coffre"):
                self.depot_coffre(st)
        if a.get("service"):
            self.servir(st)
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
              "lieu": self.lieu_de(lit), "mode": "sommeil", "charge": "sommeil", "posture": "allongé", "phase_sommeil": phase}
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
        self.achat = None
        if self.coucher:
            if i >= self.coucher[1]:
                self.dormir("Sommeil")
            else:
                lit = self.piece_pour(self.A["coucher"]["lieu"])
                self.pousser({"action": "Cherche le sommeil.", "pensee": None, "piece": lit, "lieu": self.lieu_de(lit), "mode": "eveille",
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
        if self.fatigue(a, i):
            return
        score, besoin = self.utilite(a, d, f, i)[0]
        if besoin:
            b = self.A[besoin]
            piece = self.piece_pour(b["lieu"], meme_site=True)
            v = round(self.sim.besoins[b["besoin"]], 1)
            if self.sim.piece not in self.sim.graph:
                # sur place, dans un lieu public
                self.decisions.append(f"{hm(i)} : {b['besoin']} sous le seuil d'alerte ({v}) ; y répond sur place, pendant « {e['action']} ».")
                lieu = self.sim.steps[-1]["lieu"] if self.sim.steps else "exterieur"
                self.emettre(dict(b, texte=b["texte"].replace("S'interrompt pour", "S'éclipse un instant pour").rstrip(".") + ", sur place."),
                             "Besoin pressant", "interruption", self.sim.piece, True, garder_appareils=True, lieu=lieu)
            elif v < self.SEUILS[b["besoin"]]:
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
        elif a.get("au_commerce"):
            # dans la salle où le commerçant sert ses clients (commerce.salle), au lieu de l'étape
            piece, lieu = self.COMMERCE.get("salle", e["lieu"]), e["lieu"]
        elif a.get("exterieur"):
            piece, lieu = a.get("piece", e["lieu"]), "exterieur"
        elif a.get("lieu_phase"):
            piece = self.piece_pour(a["lieu_phase"]) or e["lieu"]
        elif e["lieu"] in self.sim.graph:
            piece = e["lieu"]
        else:
            piece = self.piece_pour(a["lieu"]) or self.sim.piece
        if lieu == "domicile":
            lieu = self.lieu_de(piece)
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
        # à pied depuis un logement sans site (immeuble) : il sort sur le palier, descend, marche, remonte
        etage = (self.fiche.get("immeuble") or {}).get("etage_appartement")
        if premier and a.get("sort") and "sortie" not in extra:
            extra["sortie"] = True
            if etage:
                extra["escalier"] = {"sens": "descente"}
        if premier and a.get("rentre") and "retour" not in extra:
            extra["retour"] = True
            if etage:
                extra["escalier"] = {"sens": "montee"}
        if a.get("trajet") and self.APPRO.get("distance_m"):
            extra["parcours"] = [{"moyen": "marche", "distance_m": round(self.APPRO["distance_m"] / a["duree_phase"]), "denivele_m": 0}]
        if "{liste}" in a.get("texte", ""):
            lignes = self.listes.get(d) or []
            a["texte"] = a["texte"].replace("{liste}", ", ".join(self.libelle(x) for x in lignes) or "rien")
        self.emettre(a, e["action"], r, piece, premier, avec=e.get("avec", ()), lieu=lieu, extra=extra)

    def imposer(self, debut, pas, piece, titre, remplace=False):
        """Une réaction : à partir du pas debut, ses pas (minutes, texte) remplacent ce qu'il devait faire, dans la pièce ;
        une réaction urgente (remplace) remplace aussi les réactions déjà prévues."""
        if remplace:
            self.imposes = {k: v for k, v in self.imposes.items() if k < debut}
        i = debut
        for x in pas:
            for k in range(max(1, x["minutes"] // 5)):
                if i < PAS_PAR_JOUR and i not in self.imposes:
                    self.imposes[i] = (x["texte"] if k == 0 else x.get("suite", x["texte"]), piece, titre)
                i += 1

    def impose(self):
        """Vrai si une réaction lui impose ce pas (le pas est alors décidé ici)."""
        x = self.imposes.get(self.i)
        if not x or self.coucher:
            return False
        texte, piece, titre = x
        self.etape_courante, self.achat = None, None
        self.action_courante = {"texte": texte}
        if piece not in self.sim.graph:
            piece = self.sim.piece
        if self.SITE.get(piece):
            self.site = self.SITE[piece]
        lieu = self.LIEU_DU_SITE.get(self.SITE.get(piece), "domicile") if self.SITE.get(piece) else (
            self.sim.steps[-1]["lieu"] if self.sim.steps else "domicile")
        self.pousser({"action": texte, "pensee": None, "piece": piece, "lieu": lieu, "mode": "eveille",
                      "charge": "simple", "posture": "debout"}, titre, "reaction")
        return True

    def retenu(self, texte):
        """Quelqu'un le retient (voyageur.py) : il reste où il est, debout, le temps du pas ; ce qu'il devait faire
        n'est pas fait. Faux s'il dort ou s'endort (on ne retient pas un dormeur)."""
        if self.coucher or self.etape(self.i) is None or (self.etape(self.i)[2]["activite"] in ("sommeil", "coucher")):
            return False
        self.etape_courante, self.achat = None, None
        self.action_courante = {"texte": texte}
        lieu = self.sim.steps[-1]["lieu"] if self.sim.steps else "domicile"
        self.pousser({"action": texte, "pensee": None, "piece": self.sim.piece, "lieu": lieu, "mode": "eveille",
                      "charge": "simple", "posture": "debout"}, "Retenu par un passant", "voyageur")
        return True

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
        st = {"action": a["texte"], "pensee": None, "piece": lit, "lieu": self.lieu_de(lit), "mode": "eveille", "charge": "repos", "posture": "allongé"}
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

    # ------------------------------------------------------------ son commerce
    def magasin(self):
        """Son propre commerce (section commerce de sa fiche), ou None."""
        return self.fiche.get("commerce")

    def servir(self, st):
        """Un pas au comptoir : les clients du flux déterministe (clientele.py) achètent ce que le stock du magasin permet ;
        la recette va en caisse (espèces), sur le compte (carte) ou sur l'ardoise."""
        if not self.magasin():
            return
        if self.comptoir is None:
            ardoises = self.mem.setdefault("ardoises", dict(self.fiche.get("economie", {}).get("ardoises_au_debut", {})))
            self.comptoir = Comptoir(self.fiche, self.date, self.jour, {}, ardoises)
        self.comptoir.stock = dict(self.sim.boutique)
        r = self.comptoir.pas(self.i)
        if r["texte"]:
            st["action"] = r["texte"]
        if r["ventes"]:
            st["ventes"] = r["ventes"]
        if r["clients"]:
            st["clients"] = r["clients"]
        evs = [e for e in r["ev"] if e in self.EV and e not in st.get("ev", [])]
        if evs:
            st["ev"] = st.get("ev", []) + evs
        for b, v in r.get("effets", {}).items():
            st.setdefault("effets", {})[b] = round(st.get("effets", {}).get(b, 0) + v, 2)
        for compte, v in r.get("argent", {}).items():
            st.setdefault("argent", {})[compte] = round(st.get("argent", {}).get(compte, 0) + v, 2)
        if r.get("ruptures"):
            self.decisions.append(f"{hm(self.i)} : rupture : {', '.join(r['ruptures'])}.")

    def livrer(self, st):
        """Les livraisons du matin, une fois par jour d'ouverture (commerce.livraisons) : une livraison quotidienne
        (le pain) apporte ses quantités du jour et reprend les invendus de la veille ; une livraison des jours prévus
        (le grossiste) ramène chaque produit non frais à son stock cible."""
        C = self.magasin()
        if not C or not C.get("horaires", {}).get(self.jour) or self.mem.get("livre") == self.date:
            return
        self.mem["livre"] = self.date
        cat = {c["produit"]: c for c in C["catalogue"]}
        livre, repris = {}, []
        for nom, L in C.get("livraisons", {}).items():
            if not isinstance(L, dict):
                continue
            if "jours" in L:
                if self.jour in L["jours"]:
                    for pid, c in cat.items():
                        manque = c.get("cible", 0) - self.sim.boutique.get(pid, 0)
                        if not c.get("frais") and manque > 0:
                            livre[pid] = livre.get(pid, 0) + manque
                continue
            for pid, q in L.items():
                if pid in cat and isinstance(q, dict):
                    if self.sim.boutique.get(pid, 0):
                        repris.append({"produit": pid, "quantite": self.sim.boutique[pid], "motif": f"invendus de la veille repris ({nom})"})
                    n = q.get(self.jour, q.get("defaut", 0))
                    if n:
                        livre[pid] = livre.get(pid, 0) + n
        if repris:
            st["reprises"] = repris
        # ce qu'il met de côté pour la maison dès la livraison (approvisionnement.mis_de_cote)
        P = self.sim.PRODUITS
        for x in self.APPRO.get("mis_de_cote", []) if self.COMMERCE is C else []:
            spec = P.get(x["produit"])
            n = x["unites"].get(self.jour, x["unites"].get("defaut", 0))
            cid = spec.get("magasin") if spec else None
            if n and cid in cat:
                st.setdefault("prelevements", []).append({"produit": cid, "quantite": n, "maison": x["produit"],
                                                          "quantite_maison": n * (spec.get("par_unite") or cat[cid]["quantite"])})
        if livre:
            st["livraisons"] = [{"produit": p, "quantite": q} for p, q in livre.items()]
            self.decisions.append(f"{hm(self.i)} : livraisons : {len(livre)} produits"
                                  + (f", invendus repris : {', '.join(libelle(cat[x['produit']], x['quantite']) for x in repris)}" if repris else "") + ".")

    def caisse_au_coffre(self, st):
        """À la fermeture, les espèces au-delà du fond de caisse rejoignent le coffre."""
        E = self.fiche.get("economie", {})
        fond = E.get("fond_de_caisse", E.get("caisse_au_debut"))
        if fond is None:
            return
        especes = round(self.sim.argent.get("caisse", 0) - fond, 2)
        if especes > 0:
            st["argent"] = {**st.get("argent", {}), "caisse": -especes, "coffre": especes}

    def depot_coffre(self, st):
        """À la banque, il dépose la recette du coffre sur son compte."""
        m = self.sim.argent.get("coffre", 0)
        if m > 0:
            st["argent"] = {**st.get("argent", {}), "coffre": -m, "compte": m}
            self.decisions.append(f"{hm(self.i)} : dépose la recette du coffre à la banque : {f'{m:.2f}'.replace('.', ',')} €.")

    def terminer(self):
        etat_final, stats = self.sim.terminer(self.j.extinction, self.j.endormissement)
        etat_final["habitant"] = self.mem
        self.j.ecarts = self.decisions
        self.j.bilan = ["Journée vécue par l'habitant générique."]
        return self.sim.steps, etat_final, stats
