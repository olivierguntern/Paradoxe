"""Logements partagés du quartier : ce qu'on partage quand on vit sous le même toit, ou qu'on y est en visite.

Un logement est partagé quand plusieurs habitants du quartier en ont les
pièces (un couple, des voisins invités). Le quartier (quartier.py) tient,
pour chacun de ces logements :
- les lumières : une pièce reste éclairée tant qu'un occupant éveillé y est
  et l'a allumée, ou y était quand elle l'était ; celui qui sort n'éteint plus
  sur la tête de l'autre, celui qui entre ne rallume pas une pièce éclairée ;
- les appareils : la télévision, la radio voulues par un occupant éveillé
  s'entendent chez tous ceux qui sont dans le logement (« appareils
  allumés » de leur pas, avec « partage » : ce qui est allumé par d'autres) ;
- pour un foyer (ceux qui y dorment) : un seul garde-manger (les provisions
  de tous, le stock commun) et les objets de la maison, connus de tous ; les
  croyances sur les objets restent celles de chacun ;
- les repas communs du logement (repas_communs : le déjeuner, le dîner) : le
  menu est celui du foyer, quelle que soit la fiche qui le décrit ; cuisiné
  une fois pour tous, par qui le prépare (ou le premier à table), il n'est
  pas repris par les autres. Les autres repas (le petit-déjeuner) restent
  ceux de chacun.

Un logement que personne d'autre n'a (la boutique de Robert) garde ses règles
ordinaires.
"""
import os

from agent import JOURS
from fiches import MONDE, lire


class Logements:
    def __init__(self, q):
        self.q = q
        self.salle = {}   # habitant -> {pièce de sa fiche: (logement, pièce commune)}
        for pid, h in q.H.items():
            lds = q.fiches[pid]["domicile"]["plan"].get("logements_des_sites", {})
            m = {}
            for pc in h.sim.PIECES.values():
                lg = pc.get("logement") or lds.get(pc.get("lieu"))
                if lg:
                    m[pc["id"]] = (lg, pc.get("id_local", pc["id"].split(":")[-1]))
            self.salle[pid] = m
        compte = {}
        for m in self.salle.values():
            for lg in {k[0] for k in m.values()}:
                compte[lg] = compte.get(lg, 0) + 1
        self.partages = {lg for lg, n in compte.items() if n > 1}
        self.lumieres = {k for pid, m in self.salle.items() for p, k in m.items()
                         if k[0] in self.partages and q.H[pid].sim.lumieres.get(p)}
        self.lieu_appareil = {}   # (habitant, appareil) -> logement où il l'a allumé
        self.foyers = {}
        for pid, h in q.H.items():
            lit = h.piece_pour(h.A["sommeil"]["lieu"])
            lg = self.salle[pid].get(lit, (None,))[0]
            if lg in self.partages:
                self.foyers.setdefault(lg, []).append(pid)
        for lg, pids in self.foyers.items():
            if len(pids) > 1:
                self.mettre_en_commun([q.H[p] for p in pids])
                f = os.path.join(MONDE, "logements", f"{lg}.json")
                communs = lire(f).get("repas_communs") if os.path.exists(f) else None
                if communs:
                    self.repas_en_commun([q.H[p] for p in pids], communs)

    @staticmethod
    def mettre_en_commun(membres):
        """Un foyer : un seul stock de provisions (celui de qui en a le plus, complété des autres) et les objets de tous."""
        base = max(membres, key=lambda h: len(h.sim.PRODUITS))
        stock, produits, positions = base.sim.stock, {}, {}
        for h in membres:
            produits.update(h.sim.PRODUITS)
            positions.update(h.sim.positions)
            for k, v in h.sim.stock.items():
                stock.setdefault(k, v)
        for h in membres:
            h.sim.stock, h.sim.PRODUITS, h.sim.positions = stock, produits, positions
            for o, ou in positions.items():
                h.sim.croyances.setdefault(o, ou)

    @staticmethod
    def repas_en_commun(membres, communs):
        """Les repas communs : le menu du foyer (de la première fiche qui le décrit) chez chacun, servis une fois pour tous."""
        menus = {}
        for h in membres:
            for k, v in h.MENUS.items():
                if k in communs:
                    menus.setdefault(k, v)
                elif k in JOURS:
                    for m in communs:
                        if m in v:
                            menus.setdefault(k, {}).setdefault(m, v[m])
        faits = {}
        for h in membres:
            M = {k: dict(v) if k in JOURS else v for k, v in h.MENUS.items()}
            for k, v in menus.items():
                if k in JOURS:
                    M.setdefault(k, {}).update(v)
                else:
                    M[k] = v
            h.MENUS, h.foyer = M, (set(communs), faits)

    def apres_pas(self):
        """Après le pas de chacun : lumières et appareils des logements partagés, tels que les vivent tous les occupants."""
        q, present, occupants = self.q, {}, {}
        for pid, h in q.H.items():
            s = h.sim.steps[-1]
            k = self.salle[pid].get(s["piece"])
            if k and k[0] in self.partages and "phase_sommeil" not in s:
                present.setdefault(k, []).append(pid)
                occupants.setdefault(k[0], []).append(pid)
        # lumières : allumée par un occupant éveillé qui y est, ou déjà allumée et quelqu'un y est encore
        allumees = {k for k in self.lumieres if present.get(k)}
        for pid, m in self.salle.items():
            for p, k in m.items():
                if k in present and pid in present[k] and q.H[pid].sim.lumieres.get(p):
                    allumees.add(k)
        self.lumieres = allumees
        for pid, m in self.salle.items():
            for p, k in m.items():
                if k[0] in self.partages:
                    q.H[pid].sim.lumieres[p] = k in allumees
        # appareils : ceux que veut un occupant éveillé, entendus de tous ceux qui sont dans le logement
        voulus = {}
        for lg, pids in occupants.items():
            for pid in pids:
                k = self.salle[pid][q.H[pid].sim.steps[-1]["piece"]]
                for a in q.H[pid].sim.appareils:
                    if self.lieu_appareil.setdefault((pid, a), k[0]) == lg:
                        voulus.setdefault(lg, set()).add(a)
        for lg, pids in occupants.items():
            for pid in pids:
                s = q.H[pid].sim.steps[-1]
                vus = set(s["appareils_allumes"])
                ajout = set(voulus.get(lg, ()))
                if self.salle[pid][s["piece"]] in allumees:
                    ajout.add(f"lumiere-{s['piece']}")
                ajout -= vus
                if ajout:
                    s["appareils_allumes"] = sorted(vus | ajout)
                    s["partage"] = {"allumes_par_d_autres": sorted(ajout)}
