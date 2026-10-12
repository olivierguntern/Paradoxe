"""Clientèle d'un commerce : flux déterministe de clients anonymes et règles de vente.

Les clients anonymes ne sont pas simulés : à chaque pas d'ouverture, leur
nombre est tiré autour de l'affluence moyenne de l'heure (loi de Poisson),
puis chacun compose un panier d'un à quatre articles selon les poids du moment
de la journée (fiche, commerce.paniers). Les habitués nommés de la fiche
viennent à leur heure, les jours prévus, avec leur panier et leurs propos.

Le flux ne dépend que de la date et de l'heure : la journée de référence
rédigée à la main et l'agent du commerçant voient exactement les mêmes
clients. Ce qui est vendu dépend en revanche du stock du magasin au moment du
passage : un produit épuisé n'est pas vendu (rupture).
"""
import math
import zlib

GENRE = {"pack": "m", "boîte": "f", "brique": "f", "plaquette": "f", "paquet": "m", "tablette": "f", "morceau": "m", "sachet": "m",
         "bouteille": "f", "pièce": "f", "barquette": "f", "sac": "m", "bidon": "m", "pommes": "f", "oranges": "f", "bananes": "f",
         "oignons": "m", "baguettes": "f", "pains": "m", "laitues": "f"}
NOMBRES = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix"]
PORTRAITS = ["une dame âgée", "un ouvrier du chantier de la place", "une jeune mère avec sa poussette", "un étudiant", "un retraité en casquette",
             "une infirmière qui sort de garde", "un monsieur en costume", "une adolescente", "un livreur", "une voisine de la rue d'Ivry",
             "un couple de touristes", "un peintre du quartier", "une dame avec son chien", "un jeune homme pressé", "une employée de la mairie",
             "un vieux monsieur à canne"]


def tirage(*cle):
    """Nombre déterministe entre 0 et 1."""
    return (zlib.crc32("|".join(map(str, cle)).encode()) % 10000) / 10000


def choix(liste, *cle):
    return liste[zlib.crc32("|".join(map(str, cle)).encode()) % len(liste)]


def idx(h):
    a, b = map(int, h.split(":"))
    return (a * 60 + b) // 5


def euros(v):
    return f"{v:.2f}".replace(".", ",") + " €"


def enumerer(mots):
    return mots[0] if len(mots) == 1 else ", ".join(mots[:-1]) + " et " + mots[-1]


def libelle(c, n):
    """« une baguette », « quatre pommes », « deux paquets de pâtes »."""
    if c["vente"] in ("à la pièce", "pièce"):
        nom = c["nom"].split(" (")[0]
        if c["vente"] == "pièce":
            if n == 1:
                return ("une " if GENRE.get(c["unite"]) == "f" else "un ") + nom
            return f"{NOMBRES[n] if n <= 10 else n} {c['unite']}"
        if n == 1:
            return ("une " if GENRE.get(c["unite"]) == "f" else "un ") + c["unite"][:-1]
        return f"{NOMBRES[n] if n <= 10 else n} {c['unite']}"
    base = c["nom"].split(" (")[0]
    de = "d'" if base[0].lower() in "aeiouyhéèêœ" else "de "
    if n == 1:
        return ("une " if GENRE.get(c["vente"]) == "f" else "un ") + f"{c['vente']} {de}{base}"
    pluriel = c["vente"] if c["vente"].endswith(("s", "x")) else c["vente"] + "s"
    return f"{NOMBRES[n] if n <= 10 else n} {pluriel} {de}{base}"


class Clientele:
    """Clients d'une journée d'ouverture, pas par pas."""

    PAIEMENTS = {"especes": "caisse", "carte": "compte", "ardoise": "ardoises"}

    def __init__(self, commerce, date, jour):
        self.C = commerce
        self.date, self.jour = date, jour
        A = commerce["affluence_clients_par_pas"]
        self.reperes = sorted((idx(h), v) for h, v in A.items() if h != "principe")
        self.cat = {c["produit"]: c for c in commerce["catalogue"]}
        self.habitues = {}
        for h in commerce["clients_habitues"]:
            if self.jour in h["jours"]:
                self.habitues.setdefault(idx(h["heure"]), []).append(h)

    def moyenne(self, i):
        return next((v for h, v in reversed(self.reperes) if h <= i), 0.0)

    def nombre(self, i):
        """Nombre de clients anonymes au pas i : quantile de Poisson d'un tirage déterministe."""
        lam, u = self.moyenne(i), tirage(self.date, i, "clients")
        k, p = 0, math.exp(-lam)
        cumul = p
        while u > cumul and k < 8:
            k += 1
            p *= lam / k
            cumul += p
        return k

    @staticmethod
    def moment(i):
        return "matin" if i < idx("11:00") else ("midi" if i < idx("16:00") else "soir")

    def panier(self, i, k):
        poids = dict(self.C["paniers"][self.moment(i)])
        u = tirage(self.date, i, k, "articles")
        n = 1 if u < 0.4 else (2 if u < 0.72 else (3 if u < 0.9 else 4))
        articles = []
        for a in range(n):
            total = sum(poids.values())
            x = tirage(self.date, i, k, "produit", a) * total
            for pid, w in poids.items():
                x -= w
                if x < 0:
                    break
            q = 1
            if pid in self.C.get("par_plusieurs", {}):
                lo, hi = self.C["par_plusieurs"][pid]
                q = lo + int(tirage(self.date, i, k, "quantite", a) * (hi - lo + 1))
            articles.append([pid, q])
            poids.pop(pid)
        return articles

    def clients(self, i):
        """Clients qui entrent au pas i : habitués d'abord, puis anonymes."""
        out = []
        for h in self.habitues.get(i, []):
            propos = h["propos"].get(self.jour) or {}
            articles = [list(a) for a in h["panier"]] + [list(a) for a in propos.get("ajoute", [])]
            out.append({"habitue": h["nom"], "articles": articles, "propos": propos.get("texte"), "reponse": propos.get("reponse"),
                        "paiement": propos.get("paiement", h.get("paiement", "especes")), "rembourse": propos.get("rembourse", False)})
        for k in range(self.nombre(i)):
            out.append({"articles": self.panier(i, k), "portrait": choix(PORTRAITS, self.date, i, k, "portrait"),
                        "u_paiement": tirage(self.date, i, k, "paiement"), "u_humeur": tirage(self.date, i, k, "humeur")})
        return out

    # ------------------------------------------------------------ vente
    def servir(self, i, stock, clients=None, ardoises=None):
        """Vend aux clients du pas ce que le stock permet. Le stock (dict) et les ardoises (dict par client) sont mis à jour.

        Renvoie les lignes de vente (format du moteur), le nombre de clients, la recette par mode
        de paiement, les remboursements d'ardoise et, client par client, ce qu'il faut pour le récit."""
        clients = self.clients(i) if clients is None else clients
        ventes, textes = [], []
        recu, rembourse_total = {}, 0.0
        for cl in clients:
            lignes, manque = [], []
            for pid, n in cl["articles"]:
                q = min(n, stock.get(pid, 0))
                if q < n:
                    manque.append(pid)
                if q:
                    stock[pid] -= q
                    lignes.append((pid, q))
            total = round(sum(q * self.cat[pid]["prix"] for pid, q in lignes), 2)
            if "habitue" in cl:
                paiement = cl["paiement"]
            else:
                p_carte = 0.0 if total < 5 else (0.3 if total < 10 else 0.7)
                paiement = "carte" if cl["u_paiement"] < p_carte else "especes"
            for pid, q in lignes:
                ventes.append({"produit": pid, "quantite": q, "paiement": paiement})
            if lignes:
                recu[paiement] = round(recu.get(paiement, 0) + total, 2)
            if paiement == "ardoise" and ardoises is not None and lignes:
                ardoises[cl["habitue"]] = round(ardoises.get(cl["habitue"], 0) + total, 2)
            rembourse = 0.0
            if cl.get("rembourse") and ardoises is not None and ardoises.get(cl["habitue"]):
                rembourse = ardoises.pop(cl["habitue"])
                rembourse_total = round(rembourse_total + rembourse, 2)
            reponse = (cl.get("reponse") or "").replace("{montant}", euros(rembourse).replace(" €", " euros"))
            textes.append({"qui": cl.get("habitue") or cl["portrait"], "lignes": lignes, "total": total, "paiement": paiement,
                           "manque": manque, "habitue": "habitue" in cl, "propos": cl.get("propos"), "reponse": reponse or None,
                           "rembourse": rembourse, "presse": cl.get("u_humeur", 1) < 0.05,
                           "familier": "habitue" not in cl and 0.05 <= cl.get("u_humeur", 1) < 0.17})
        return {"ventes": ventes, "n": len(clients), "recu": recu, "rembourse": rembourse_total, "clients": textes}

    def raconter(self, res):
        """Texte d'un pas de service : qui entre, ce qui se dit, ce qui est vendu et comment c'est payé."""
        morceaux = []
        for t in res["clients"]:
            panier = enumerer([libelle(self.cat[pid], q) for pid, q in t["lignes"]]) if t["lignes"] else None
            pay = {"especes": "", "carte": ", par carte", "ardoise": ", sur l'ardoise"}[t["paiement"]]
            manque = enumerer([self.cat[pid]["nom"].split(" (")[0] for pid in t["manque"]]) if t["manque"] else None
            if t["habitue"]:
                plur = t["qui"].lower().startswith("les ")
                m = f"{t['qui'][0].upper() + t['qui'][1:]} {'entrent' if plur else 'entre'}."
                if t["propos"]:
                    m += f" « {t['propos']} »" + (f" Robert : « {t['reponse']} »" if t["reponse"] else "")
                if panier:
                    m += f" {'Leur' if plur else 'Lui'} sert {panier} ({euros(t['total'])}{pay})."
                if t["rembourse"]:
                    m += f" Elles règlent l'ardoise de mercredi : {euros(t['rembourse'])}, qu'il raye du carnet."
            else:
                qui = t["qui"]
                if panier:
                    m = f"{qui} : {panier} ({euros(t['total'])}{pay})"
                else:
                    m = f"{qui} repart sans rien"
                if t["familier"]:
                    m += ", avec quelques mots sur le quartier"
                if t["presse"]:
                    m += ", en regardant sa montre"
                m += "."
            if manque:
                m += f" Plus de {manque} : il s'excuse."
            morceaux.append(m)
        if not morceaux:
            return None
        anonymes = [m for t, m in zip(res["clients"], morceaux) if not t["habitue"]]
        nommes = [m for t, m in zip(res["clients"], morceaux) if t["habitue"]]
        txt = " ".join(nommes)
        if len(anonymes) == 1:
            txt += (" " if txt else "") + "Sert " + anonymes[0]
        elif anonymes:
            n = len(anonymes)
            txt += (" " if txt else "") + f"Sert {NOMBRES[n] if n <= 10 else n} clients à la suite. " + " ".join(m[0].upper() + m[1:] for m in anonymes)
        return txt


class Comptoir:
    """Service au comptoir, pas par pas, pour la journée rédigée comme pour l'agent du commerçant.

    Tient le compte des pas sans client (boutique vide) et des ruptures déjà constatées ;
    renvoie pour chaque pas les ventes, les événements vécus, l'effet sur le besoin social
    et le texte de ce qui se passe au comptoir."""

    def __init__(self, fiche, date, jour, stock, ardoises=None):
        self.fiche = fiche
        self.cl = Clientele(fiche["commerce"], date, jour)
        self.stock = stock
        self.ardoises = {} if ardoises is None else ardoises
        self.vides = 0
        self.ruptures = []
        self.nb_clients = 0
        self.recette = 0.0
        S = fiche["besoins"]["social"]["satisfaction"]
        self.social_client, self.social_habitue = S["client_par_pas"], S["habitue"]

    def pas(self, i, clients=None):
        res = self.cl.servir(i, self.stock, clients, self.ardoises)
        out = {"ventes": res["ventes"], "clients": res["n"], "ev": [], "texte": self.cl.raconter(res)}
        self.nb_clients += res["n"]
        self.recette = round(self.recette + sum(res["recu"].values()), 2)
        if res["rembourse"]:
            out["argent"] = {"ardoises": -res["rembourse"], "caisse": res["rembourse"]}
        if res["n"] == 0:
            self.vides += 1
            if self.vides == 4:
                out["ev"].append("boutique_vide")
                self.vides = 0
            return out
        self.vides = 0
        social = self.social_client * min(res["n"], 3)
        if res["n"] >= 3:
            out["ev"].append("affluence")
        if any(t["presse"] for t in res["clients"]):
            out["ev"].append("client_presse")
        if any(t["habitue"] or t["familier"] for t in res["clients"]):
            out["ev"].append("client_habitue")
        if any(t["habitue"] for t in res["clients"]):
            social += self.social_habitue
        nouvelles = []
        for t in res["clients"]:
            for pid in t["manque"]:
                nom = self.cl.cat[pid]["nom"].split(" (")[0]
                if nom not in self.ruptures:
                    self.ruptures.append(nom)
                    nouvelles.append(nom)
        if nouvelles:
            out["ev"].append("rupture_stock")
            out["ruptures"] = nouvelles
        out["effets"] = {"social": round(social, 2)}
        return out
