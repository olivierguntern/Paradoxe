"""Éléments communs aux journées rédigées de Robert Chazal.

Les journées de Robert sont rédigées à la main comme celles de Thomas
Berthier ; ce module ne fait que les gestes répétés d'un jour à l'autre :
découpe d'un trajet en Kangoo en pas de 5 minutes, nuit en cycles de
sommeil, et pas de service au comptoir. Les clients anonymes viennent du
flux déterministe de outils/clientele.py ; ce qui est vendu dépend du stock
du magasin, tenu ici à jour au fil de la rédaction (livraisons, reprises,
prélèvements, ventes), puis revérifié par le moteur.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from clientele import Comptoir, enumerer, euros, libelle  # noqa: E402,F401  (euros : réexporté pour les journées)
from moteur import hm, idx, p, voiture  # noqa: E402

BOUTIQUE = "epicerie-chazal"
KANGOO = "Kangoo"
TRAJET = "trajet-voiture"

# Découpe du trajet de 5,2 km (fiche, trajets) en pas de 5 minutes : distance en mètres et dénivelé.
# À l'aube et à midi, 15 minutes ; le soir, dans les bouchons, 20 minutes ; le lundi matin, 20 minutes.
ALLER = [(1900, 0), (1500, 0), (1800, 85)]
ALLER_LENT = [(1300, 0), (1300, 0), (1200, 0), (1400, 85)]
RETOUR = [(1800, -85), (1500, 0), (1900, 0)]
RETOUR_LENT = [(1300, -85), (1200, 0), (1400, 0), (1300, 0)]


def nuit(cycles):
    """Pas de sommeil à partir de cycles (début, fin, phase, rêve, événement du rêve[, texte])."""
    out = []
    for d, f, phase, reve, ev, *texte in cycles:
        for k in range(idx(d), idx(f)):
            txt = texte[0] if texte else ("Dort." if phase != "micro-éveil" else "Se retourne, entend Josiane respirer, se rendort.")
            out.append(p(txt, phase_sommeil=phase, reve=reve, ev=[ev] if (ev and k == idx(d)) else []))
    return out


def en_voiture(textes, decoupe, pensees=(), ev=(), extra=None):
    """Pas d'un trajet en Kangoo : un texte par pas, la distance et le dénivelé de la découpe."""
    out = []
    for k, (txt, (dist, den)) in enumerate(zip(textes, decoupe)):
        st = p(txt, pensees[k] if k < len(pensees) else None, parcours=[voiture(dist, den)], piece=KANGOO, lieu=TRAJET,
               posture="assis", charge="conduite", ev=list(ev[k]) if k < len(ev) and ev[k] else [])
        if extra and k in extra:
            for cle, v in extra[k].items():
                st[cle] = v
        out.append(st)
    return out


def depart_maison():
    """Objets pris dans l'entrée en partant, et la Kangoo qui quitte le garage."""
    return {"prendre": [("obj-veste", "entree / portemanteau", "porté"), ("obj-cles", "entree / vide-poche", "poche de la veste"),
                        ("obj-cles-kangoo", "entree / vide-poche", "dans sa main"), ("obj-portefeuille", "entree / vide-poche", "poche de la veste")],
            "sortir": [("obj-kangoo", "garage / place de la Kangoo", "en route"), ("obj-cles-kangoo", "dans sa main", "contact de la Kangoo")]}


def mvs(liste):
    return [{"objet": o, "de": a, "vers": b} for o, a, b in liste]


ARRIVEE_BOUTIQUE = [("obj-kangoo", "en route", "cour-epicerie / place louée"), ("obj-cles-kangoo", "contact de la Kangoo", "poche de la blouse"),
                    ("obj-veste", "porté", "arriere-boutique / patère"), ("obj-blouse", "arriere-boutique / patère", "porté"),
                    ("obj-cles", "poche de la veste", "poche de la blouse")]
DEPART_BOUTIQUE = [("obj-blouse", "porté", "arriere-boutique / patère"), ("obj-veste", "arriere-boutique / patère", "porté"),
                   ("obj-cles", "poche de la blouse", "poche de la veste"), ("obj-cles-kangoo", "poche de la blouse", "contact de la Kangoo"),
                   ("obj-kangoo", "cour-epicerie / place louée", "en route")]
ARRIVEE_MAISON = [("obj-kangoo", "en route", "garage / place de la Kangoo"), ("obj-cles-kangoo", "contact de la Kangoo", "entree / vide-poche"),
                  ("obj-cles", "poche de la veste", "entree / vide-poche"), ("obj-portefeuille", "poche de la veste", "entree / vide-poche"),
                  ("obj-veste", "porté", "entree / portemanteau")]


class Magasin:
    """Stock du magasin tenu au fil de la rédaction, et comptoir du jour."""

    def __init__(self, fiche, etat, date, jour):
        self.fiche = fiche
        self.cat = {c["produit"]: c for c in fiche["commerce"]["catalogue"]}
        self.stock = dict(etat["boutique"])
        self.caisse = etat["argent"]["caisse"]
        self.comptoir = Comptoir(fiche, date, jour, self.stock)
        self.fond = fiche["economie"]["caisse_au_debut"]

    def commande(self):
        """Bon de commande du grossiste : chaque produit sec ou frais de rayon ramené à son stock cible."""
        return {pid: c["cible"] - self.stock[pid] for pid, c in self.cat.items() if not c.get("frais") and c["cible"] > self.stock[pid]}

    def livrer(self, quantites):
        for pid, q in quantites.items():
            self.stock[pid] += q
        return [{"produit": pid, "quantite": q} for pid, q in quantites.items() if q]

    def reprendre(self, quantites, motif):
        for pid, q in quantites.items():
            self.stock[pid] -= q
        return [{"produit": pid, "quantite": q, "motif": motif} for pid, q in quantites.items() if q]

    def prelever(self, pid, q, maison, qm):
        self.stock[pid] -= q
        return {"produit": pid, "quantite": q, "maison": maison, "quantite_maison": qm}

    def pour_maison(self, maison, n, produit=None):
        """Prélèvement de n unités de vente pour une provision de la maison (correspondance de la fiche)."""
        spec = next(x for x in self.fiche["domicile"]["provisions_au_debut"] if x["id"] == maison)
        return self.prelever(produit or spec["magasin"], n, maison, n * spec["par_unite"])

    def texte(self, quantites, limite=None):
        items = [libelle(self.cat[pid], q) for pid, q in quantites.items() if q]
        if limite and len(items) > limite:
            return enumerer(items[:limite] + [f"{len(items) - limite} autres produits"])
        return enumerer(items)

    def service(self, debut, fin, titre, routine, vide, notes):
        """Pas d'ouverture de debut à fin. Les clients du flux sont servis à chaque pas ;
        notes[heure] ajoute ce que Robert fait d'autre (action, pensée, événements, effets, déplacements) ;
        vide[k] décrit, dans l'ordre, les pas sans client et sans note."""
        out, k = [], 0
        for i in range(idx(debut), idx(fin)):
            n = dict(notes.get(hm(i), {}))
            client = n.pop("client", None)
            if client:
                # le client simulé est servi le premier : ses achats sortent du stock avant ceux du flux
                for v in client.get("ventes", []):
                    self.stock[v["produit"]] -= v["quantite"]
                    if self.stock[v["produit"]] < 0:
                        raise ValueError(f"{hm(i)} : stock insuffisant de {v['produit']} pour le client simulé")
            r = self.comptoir.pas(i)
            if client:
                r_txt = client["texte"] + ((" Puis " + r["texte"][0].lower() + r["texte"][1:]) if r["texte"] else "")
                r["ventes"] = client.get("ventes", []) + r["ventes"]
                r["clients"] += 1 if client.get("ventes") else 0
                r["ev"] = list(dict.fromkeys(client.get("ev", []) + r["ev"]))
                r.setdefault("effets", {})
                r["effets"]["social"] = round(r["effets"].get("social", 0) + client.get("social", 0), 2)
                r["texte"] = r_txt
            action, apres = n.pop("action", None), n.pop("apres", None)
            if action and r["texte"]:
                txt = action + " " + r["texte"]
            elif action or r["texte"]:
                txt = action or r["texte"]
            else:
                txt = vide[k % len(vide)]
                k += 1
            if apres:
                txt += " " + apres
            effets = dict(r.get("effets", {}))
            for e, v in n.pop("effets", {}).items():
                effets[e] = v if (v == "vide" or isinstance(v, bool)) else round(effets.get(e, 0) + v, 2)
            st = p(txt, n.pop("pensee", None), ventes=r["ventes"], clients=r["clients"], ev=list(dict.fromkeys(n.pop("ev", []) + r["ev"])),
                   mode="travail", charge="service", posture="debout", radio=True, piece="boutique", lieu=BOUTIQUE)
            if effets:
                st["effets"] = effets
            if r.get("ruptures"):
                st["ruptures"] = r["ruptures"]
            if r.get("argent"):
                st["argent"] = r["argent"]
            st.update(n)
            for v in st["ventes"]:
                if v["paiement"] == "especes":
                    self.caisse = round(self.caisse + v["quantite"] * self.cat[v["produit"]]["prix"], 2)
            self.caisse = round(self.caisse + st.get("argent", {}).get("caisse", 0), 2)
            if not st["ventes"]:
                del st["ventes"]
            if not st["clients"]:
                del st["clients"]
            out.append(st)
        return out

    def recette(self):
        return self.comptoir.recette

    def vider_caisse(self):
        """Espèces à passer de la caisse à la sacoche du coffre : tout ce qui dépasse le fond de caisse."""
        m = round(self.caisse - self.fond, 2)
        self.caisse = self.fond
        return {"caisse": -m, "coffre": m}, m


def ingredients(fiche, jour, moment):
    """Consommation d'un repas du menu de la fiche (quantités pour le couple)."""
    M = fiche["menus_prevus"]
    repas = M["petit_dejeuner"] if moment == "petit_dejeuner" else M[jour][moment]
    return [{"produit": pid, "quantite": q} for pid, q in repas["ingredients"]]


def articles_client(cat, achats):
    """Lignes de vente au comptoir à partir des achats d'un client simulé (quantités dans ses unités)."""
    return [{"produit": a["produit"], "quantite": round(a["quantite"] / cat[a["produit"]]["quantite"]),
             "paiement": "especes"} for a in achats]
