"""Le voyageur de Paradoxe : ses interventions dans le monde joué.

Un scénario (data/voyageur/<nom>.json) liste ses interventions, chacune à une
date et une heure :
- deplacer : il déplace un objet d'un habitant, à son insu (la réalité change,
  pas ce que l'habitant croit) ;
- retenir : il aborde un habitant et le retient un moment ; ce que l'habitant
  devait faire pendant ce temps n'est pas fait (des courses qui auraient dû
  commencer sont abandonnées) ;
- acheter : il achète dans le commerce d'un habitant, sur le stock du magasin ;
- parler : il dit quelque chose à un habitant éveillé, qui le retient ;
- passer : il se tient un moment dans un lieu (lieu et pièce, ou là où est un
  habitant), sans rien faire d'autre que d'y être vu.

Anachronismes : le voyageur porte des objets (« porte » du scénario) et peut
s'en servir pendant une intervention (« utilise »). Ce qui est apparu après
l'époque (data/monde/epoque.json) est une anomalie : chaque habitant éveillé
au même endroit que lui peut la remarquer, selon sa visibilité, son attention
et sa concentration (tirage déterministe), mieux s'il lui fait face. Une
anomalie remarquée fait vivre l'événement anachronisme_remarque, reste en
mémoire (« anomalies ») et se raconte ensuite (quartier.py).

Pour les habitants, le voyageur n'est qu'un passant. Le quartier (quartier.py)
appelle le voyageur à chaque pas : retenir() avant que chacun décide, agir()
une fois les décisions prises, avant le calcul du pas. Le monde de référence
est le même quartier sans voyageur.
"""
import os
import zlib

from fiches import MONDE, lire
from moteur import hm, idx


def tirage(*cle):
    return (zlib.crc32("|".join(map(str, cle)).encode()) % 10000) / 10000


class Voyageur:
    def __init__(self, scenario):
        self.scenario = scenario
        self.I = scenario["interventions"]
        self.journal = []   # ce que le voyageur a fait : (date, heure, texte)
        self.E = lire(os.path.join(MONDE, "epoque.json"))
        self.porte = scenario.get("porte", [])
        self.temoins = set()   # habitants qui ont remarqué un anachronisme de leurs propres yeux
        inconnus = [o for x in self.I for o in x.get("utilise", [])] + self.porte
        for o in inconnus:
            if o not in self.E["objets"]:
                raise ValueError(f"objet inconnu de l'époque : {o}")

    def cibles(self):
        """Habitants touchés directement : visés par une intervention (le commerçant pour un achat), ou témoins d'un
        anachronisme (à appeler après la simulation)."""
        return sorted({x.get("habitant") or x.get("commerce") for x in self.I if x["type"] != "passer" or x.get("habitant")} | self.temoins)

    def objets(self, pid, date):
        """Déplacements d'objets de l'habitant ce jour-là, au format des perturbations du moteur."""
        return [{"date": x["date"], "heure": x["heure"], "objet": x["objet"], "vers": x["vers"], "par": "voyageur"}
                for x in self.I if x["type"] == "deplacer" and x["habitant"] == pid and x["date"] == date]

    def noter(self, q, i, texte):
        if (q.date, hm(i), texte) not in self.journal:
            self.journal.append((q.date, hm(i), texte))

    def retenir(self, q, pid, h):
        """Vrai si le voyageur retient l'habitant à ce pas (le pas est alors décidé ici)."""
        i = h.i
        for x in self.I:
            if x["type"] != "retenir" or x["habitant"] != pid or x["date"] != q.date:
                continue
            d = idx(x["heure"])
            f = d + max(1, x.get("duree_minutes", 5) // 5)
            if d <= i < f:
                if (d, f) not in h.retenues:
                    h.retenues.append((d, f))
                texte = x.get("texte") or "Un passant l'aborde, lui demande son chemin et le retient en bavardant."
                if h.retenu(texte):
                    if i == d:
                        h.decisions.append(f"{hm(i)} : un passant le retient {x.get('duree_minutes', 5)} minutes.")
                        self.noter(q, i, f"retient {q.prenom(pid)} {x.get('duree_minutes', 5)} minutes")
                    return True
        return False

    def agir(self, q):
        """Achats et paroles du pas, une fois que chacun a décidé de son pas."""
        i = min(h.i for h in q.H.values())
        for x in self.I:
            if x["date"] != q.date or idx(x["heure"]) != i:
                continue
            if x["type"] == "acheter":
                self.acheter(q, x, i)
            elif x["type"] == "parler":
                self.parler(q, x, i)
        self.etre_vu(q, i)

    # ------------------------------------------------------------ anachronismes
    def ou_est_il(self, q, x, i):
        """Où est le voyageur pendant l'intervention x au pas i, et à qui fait-il face : (endroit, habitant) ou None."""
        d = idx(x["heure"])
        f = d + max(1, x.get("duree_minutes", 5) // 5) if x["type"] in ("retenir", "passer") else d + 1
        if x["date"] != q.date or not d <= i < f or x["type"] == "deplacer":
            return None
        if x["type"] == "acheter":
            o = q.H.get(x["commerce"])
            C = o.magasin() if o else None
            return ((C["id"], C.get("salle", C["id"])), x["commerce"]) if C else None
        qui = x.get("habitant")
        if qui in q.H and q.H[qui].attente:
            return q.ou(qui, q.H[qui]), (qui if x["type"] != "passer" else None)
        if x["type"] == "passer" and x.get("lieu"):
            return (x["lieu"], x.get("piece", x["lieu"])), None
        return None

    def etre_vu(self, q, i):
        """Les habitants éveillés au même endroit que le voyageur peuvent remarquer ce qu'il porte ou utilise d'anachronique."""
        E = self.E
        for x in self.I:
            place = self.ou_est_il(q, x, i)
            if not place:
                continue
            endroit, face = place
            visibles = {o: E["objets"][o]["visibilite"] for o in self.porte}
            for o in x.get("utilise", []):
                visibles[o] = E["objets"][o]["visibilite_utilise"]
            for pid, h in q.H.items():
                s = h.attente[1]
                if s["mode"] == "sommeil" or q.ou(pid, h) != endroit:
                    continue
                vus = {a["objet"] for a in h.mem.get("anomalies", [])}
                attention = (q.fiches[pid].get("perception") or {}).get("attention", {}).get("piece", E["attention_ordinaire"]) / E["attention_ordinaire"]
                for o, vis in visibles.items():
                    spec = E["objets"][o]
                    if spec["apparition"] <= E["annee"] or o in vus or not vis:
                        continue
                    p = min(1.0, vis * attention * (1 - E["effet_concentration"] * h.sim.conc) * (E["face_a_face"] if pid == face else 1))
                    if tirage(q.date, i, pid, o, "anachronisme") < p:
                        st = h.attente[0]
                        st["action"] = st["action"].rstrip() + f" Remarque {spec['remarque']}."
                        if "anachronisme_remarque" in h.EV and "anachronisme_remarque" not in st.get("ev", []):
                            st.setdefault("ev", []).append("anachronisme_remarque")
                        h.mem.setdefault("anomalies", []).append({"date": q.date, "heure": hm(i), "objet": o, "quoi": spec["remarque"]})
                        h.decisions.append(f"{hm(i)} : remarque {spec['remarque']}.")
                        self.noter(q, i, f"{q.prenom(pid)} remarque : {spec['nom']}")
                        self.temoins.add(pid)

    def acheter(self, q, x, i):
        o = q.H.get(x["commerce"])
        C = o.magasin() if o else None
        if not C:
            return
        if not any(idx(a) <= i < idx(b) for a, b in C.get("horaires", {}).get(o.jour, [])):
            self.noter(q, i, f"trouve {C['nom']} fermé")
            return
        st = o.attente[0]
        reste = o.sim.boutique.get(x["produit"], 0) - sum(v["quantite"] for v in st.get("ventes", []) + st.get("prelevements", [])
                                                         if v["produit"] == x["produit"])
        n = min(x["quantite"], max(0, reste))
        c = next(c for c in C["catalogue"] if c["produit"] == x["produit"])
        nom = c["nom"].split(" (")[0]
        if not n:
            self.noter(q, i, f"ne trouve plus de {nom} chez {q.prenom(x['commerce'])}")
            return
        st["ventes"] = st.get("ventes", []) + [{"produit": x["produit"], "quantite": n, "paiement": "especes"}]
        st["clients"] = st.get("clients", 0) + 1
        prix = f"{n * c['prix']:.2f}".replace(".", ",")
        st["action"] = st["action"].rstrip() + f" Sert un passant : {n} × {nom} ({prix} €)."
        self.noter(q, i, f"achète {n} × {nom} chez {q.prenom(x['commerce'])}")

    def parler(self, q, x, i):
        h = q.H.get(x["habitant"])
        if not h or h.attente is None or h.attente[1]["mode"] == "sommeil":
            return
        st = h.attente[0]
        st["action"] = st["action"].rstrip() + f" Un passant lui dit : « {x['quoi']} »"
        st.setdefault("croise", []).append("un passant")
        h.mem.setdefault("appris", []).append({"date": q.date, "heure": hm(i), "de": "voyageur", "sujet": "voyageur", "quoi": x["quoi"]})
        self.noter(q, i, f"dit à {q.prenom(x['habitant'])} : « {x['quoi']} »")
