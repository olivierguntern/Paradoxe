"""Le voyageur de Paradoxe : ses interventions dans le monde joué.

Un scénario (data/voyageur/<nom>.json) liste ses interventions, chacune à une
date et une heure :
- deplacer : il déplace un objet d'un habitant, à son insu (la réalité change,
  pas ce que l'habitant croit) ;
- retenir : il aborde un habitant et le retient un moment ; ce que l'habitant
  devait faire pendant ce temps n'est pas fait (des courses qui auraient dû
  commencer sont abandonnées) ;
- acheter : il achète dans le commerce d'un habitant, sur le stock du magasin ;
- parler : il dit quelque chose à un habitant éveillé, qui le retient ; s'il
  annonce ce qui va se passer (« explique » : des gestes ou des traces), ce
  que l'habitant en verra, entendra ou trouvera ne lui paraîtra plus étrange :
  il ne le remarque plus comme une intrusion et n'en parle pas. Une annonce
  qui concerne le lieu d'un autre habitant (« lieu ») se raconte, elle :
  celui-ci, quand il l'apprend, y réagit comme à un bruit chez lui (il n'a
  rien demandé, lui) ;
- passer : il se tient un moment dans un lieu (lieu et pièce, ou là où est un
  habitant), sans rien faire d'autre que d'y être vu ;
- geste : il fait un geste du catalogue (data/monde/gestes.json) dans un lieu
  et une pièce : crocheter une serrure, découper une dalle, creuser, brûler,
  reboucher, couler du béton, recouvrir, nettoyer, aérer. Un geste a ses
  conditions et fait avancer la mission (« avancement ») ; il peut être vu par
  qui est dans la pièce, entendu dans tout le lieu (et des voisins, habitants
  du logement d'à côté, data/monde/voisinages.json, qui le racontent ensuite ;
  celui à qui on le raconte y réagit chez lui), et laisse des traces
  que les habitants peuvent remarquer ensuite, tant qu'elles restent. Le béton
  doit prendre avant qu'on le recouvre (« trop_tot ») ; après trop d'heures de
  gestes sans repos, le voyageur, fatigué, travaille moins bien (« fatigue »).

Tout ce qu'un habitant remarque (anachronisme, voyageur au travail, bruit,
trace) suit la même règle et le même chemin : mémoire « anomalies »,
événement vécu, bouche-à-oreille.

Réactions (data/monde/reactions.json) : chez lui (sa boutique, son
logement), un habitant ne se contente pas de remarquer. Un bruit : il va voir.
Le voyageur au travail : il le surprend, le voyageur s'enfuit et ses gestes
suivants dans ce lieu, ce jour-là, n'ont pas lieu ; il appelle la police. Une trace
d'effraction : il porte plainte et fait changer la serrure. Ces pas
remplacent ce qu'il devait faire ; ensuite il est plus vigilant dans ce lieu
et sa nouvelle serrure ne se crochète plus.

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
import datetime
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
        self.temoins = set()   # habitants qui ont remarqué quelque chose du voyageur de leurs propres yeux
        inconnus = [o for x in self.I for o in x.get("utilise", [])] + self.porte
        for o in inconnus:
            if o not in self.E["objets"]:
                raise ValueError(f"objet inconnu de l'époque : {o}")
        G = lire(os.path.join(MONDE, "gestes.json"))
        self.G, self.FATIGUE = G["gestes"], G.get("fatigue")
        self.VOISINS = lire(os.path.join(MONDE, "voisinages.json"))["voisinages"]
        self.finis = {}        # geste -> instant de la fin de sa dernière réussite
        self.effort = (None, 0.0)   # fin du dernier geste, heures de gestes depuis le dernier repos
        self.signalements = []  # ce qu'un voisin a raconté à un habitant de ce qu'il a remarqué chez lui : il y réagira
        self.avancement = {}   # avancement de la mission : accès, dalle, trou, profondeur, branche…
        self.traces = []       # traces laissées par les gestes : où, visibilité, depuis, jusqu'à
        self.echecs = []       # gestes impossibles (condition non remplie)
        self.R = lire(os.path.join(MONDE, "reactions.json"))
        self.verrous_changes = set()   # lieux dont l'habitant a fait changer la serrure
        self.fuite = {}                # lieu -> (date, instant) où le voyageur, surpris, s'est enfui : il ne revient pas ce jour-là
        for n, x in enumerate(self.I, 1):
            x["_n"] = n
            if x["type"] == "geste":
                if x["geste"] not in self.G:
                    raise ValueError(f"geste inconnu : {x['geste']}")
                if idx(x["heure"]) + self.duree(x) // 5 > 288:
                    raise ValueError(f"le geste {x['geste']} du {x['date']} à {x['heure']} passe minuit : le couper en deux")

    def cibles(self):
        """Habitants touchés directement : visés par une intervention (le commerçant pour un achat), ou témoins d'un
        anachronisme (à appeler après la simulation)."""
        return sorted({x.get("habitant") or x.get("commerce") for x in self.I if x["type"] not in ("passer", "geste") or x.get("habitant")} | self.temoins)

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
        self.gestes(q, i)
        self.etre_vu(q, i)
        self.vu_entendu(q, i)
        self.traces_remarquees(q, i)

    # ------------------------------------------------------------ anachronismes
    def ou_est_il(self, q, x, i):
        """Où est le voyageur pendant l'intervention x au pas i, et à qui fait-il face : (endroit, habitant) ou None."""
        d = idx(x["heure"])
        f = d + max(1, self.duree(x) // 5) if x["type"] in ("retenir", "passer", "geste") else d + 1
        if x["date"] != q.date or not d <= i < f or x["type"] == "deplacer":
            return None
        if x["type"] == "geste":
            return (x["lieu"], x["piece"]), None
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
                    self.remarquer(q, pid, h, i, o, spec["remarque"], vis, pid == face, x["_n"], spec["nom"], "anachronisme_remarque")

    def remarquer(self, q, pid, h, i, objet, quoi, vis, face=False, source=None, nom=None, ev="intrusion_remarquee", genre=None, lieu=None, piece=None):
        """L'habitant remarque-t-il ce qu'il voit, entend ou trouve ? Visibilité × attention relative × (1 − effet de la
        concentration), plus en face-à-face ; tirage déterministe. Ce qu'il remarque reste en mémoire et se raconte."""
        E = self.E
        if objet in {a["objet"] for a in h.mem.get("anomalies", [])}:
            return
        if objet.split(":", 1)[-1] in h.mem.get("explications", []):
            return   # on le lui a annoncé : rien d'étrange
        attention = (q.fiches[pid].get("perception") or {}).get("attention", {}).get("piece", E["attention_ordinaire"]) / E["attention_ordinaire"]
        if lieu:
            attention *= h.mem.get("vigilance", {}).get(lieu, 1.0)   # plus vigilant là où il a déjà été cambriolé
        p = min(1.0, vis * attention * (1 - E["effet_concentration"] * h.sim.conc) * (E["face_a_face"] if face else 1))
        if tirage(q.date, i, pid, objet, "anachronisme") < p:
            st = h.attente[0]
            st["action"] = st["action"].rstrip() + f" Remarque {quoi}."
            if ev in h.EV and ev not in st.get("ev", []):
                st.setdefault("ev", []).append(ev)
            h.mem.setdefault("anomalies", []).append({"date": q.date, "heure": hm(i), "objet": objet, "quoi": quoi, "source": f"V{source}"}
                                                     | ({"genre": genre, "lieu": lieu, "piece": piece} if genre and lieu else {}))
            h.decisions.append(f"{hm(i)} : remarque {quoi}.")
            self.noter(q, i, f"{q.prenom(pid)} remarque : {nom or quoi}")
            self.temoins.add(pid)
            if genre and lieu:
                self.reagir(q, pid, h, i, genre, objet, lieu, piece)

    # ------------------------------------------------------------ réactions
    @staticmethod
    def chez_lui(fiche, lieu):
        """Le lieu est-il à lui : sa boutique, ou un de ses logements ?"""
        return (fiche.get("commerce") or {}).get("id") == lieu or lieu in fiche["domicile"]["plan"].get("lieux_des_sites", {}).values()

    def reagir(self, q, pid, h, i, genre, objet, lieu, piece):
        """Chez lui, ce qu'il remarque le fait agir (data/monde/reactions.json), une fois par réaction et par lieu."""
        if not self.chez_lui(q.fiches[pid], lieu):
            return
        trace = objet.split(":", 1)[1] if ":" in objet else objet
        regle = next((r for r in self.R["regles"] if r["quand"] == genre and (not r.get("traces") or trace in r["traces"])), None)
        if not regle:
            return
        faites = h.mem.setdefault("reactions", [])
        if f"{regle['reaction']}:{lieu}" in faites:
            return
        if regle["reaction"] == "plainte" and f"surprendre:{lieu}" in faites:
            return   # il a surpris l'intrus : la police est déjà venue
        faites.append(f"{regle['reaction']}:{lieu}")
        R = self.R["reactions"][regle["reaction"]]
        h.imposer(i + 1, R["pas"], piece, R.get("titre", "Réaction à une intrusion"), remplace=bool(R.get("interrompt")))
        h.decisions.append(f"{hm(i)} : réagit ({regle['reaction'].replace('_', ' ')}).")
        self.noter(q, i, f"{q.prenom(pid)} réagit : {regle['reaction'].replace('_', ' ')}")
        if R.get("interrompt") and self.fuite.get(lieu, (None,))[0] != q.date:
            self.fuite[lieu] = (q.date, self.instant(q.date, i))
            self.noter(q, i, "surpris, le voyageur s'enfuit ; il ne revient pas dans ce lieu aujourd'hui")
        ensuite = R.get("ensuite", {})
        if ensuite.get("vigilance"):
            h.mem.setdefault("vigilance", {})[lieu] = ensuite["vigilance"]
        if ensuite.get("verrou_change"):
            self.verrous_changes.add(lieu)

    # ------------------------------------------------------------ gestes et traces
    def duree(self, x):
        return x.get("duree_minutes", self.G[x["geste"]]["duree"] if x["type"] == "geste" else 5)

    @staticmethod
    def instant(date, i):
        """Un repère de temps continu d'un jour à l'autre (pas de 5 minutes)."""
        return datetime.date.fromisoformat(date).toordinal() * 288 + i

    def gestes(self, q, i):
        """Début d'un geste : ses conditions, ses traces ; fin : ce qu'il fait avancer, efface ou atténue."""
        maintenant = self.instant(q.date, i)
        for x in self.I:
            if x["type"] != "geste" or x["date"] != q.date:
                continue
            g, d = self.G[x["geste"]], idx(x["heure"])
            f = d + max(1, self.duree(x) // 5)
            if i == d:
                manque = {k: v for k, v in g.get("si", {}).items() if self.avancement.get(k) != v}
                raison = ("il faut d'abord " + ", ".join(f"{k} {v.replace('_', ' ')}" for k, v in manque.items())) if manque else None
                if self.fuite.get(x["lieu"], (None,))[0] == q.date:
                    raison = "il a été surpris ici aujourd'hui et s'est enfui"
                elif g.get("impossible_si_verrou_change") and x["lieu"] in self.verrous_changes:
                    raison = "la serrure a été changée : elle ne se crochète plus"
                x["_ok"] = raison is None
                if raison:
                    self.echecs.append(f"{q.date} {x['heure']} : {g['nom']} n'a pas lieu ({raison})")
                    self.noter(q, i, f"ne peut pas {g['nom']} : {raison}")
                    continue
                self.noter(q, i, f"{g['nom']} ({self.duree(x)} min)")
                fin, heures = self.effort
                if not self.FATIGUE or fin is None or maintenant - fin >= self.FATIGUE["repos_heures"] * 12:
                    heures = 0.0
                x["_fatigue"] = bool(self.FATIGUE) and heures >= self.FATIGUE["seuil_heures"]
                if x["_fatigue"]:
                    self.noter(q, i, f"épuisé après {heures:g} h de travail sans repos : il travaille moins bien")
                self.effort = (maintenant + max(1, self.duree(x) // 5), heures + self.duree(x) / 60)
                traces = list(g.get("traces", []))
                tt = g.get("trop_tot")
                if tt and tt["apres"] in self.finis and maintenant - self.finis[tt["apres"]] < tt["heures"] * 12:
                    traces += tt["traces"]
                    self.noter(q, i, f"trop tôt : {self.G[tt['apres']]['nom']} il y a moins de {tt['heures']} h")
                for tr in traces:
                    self.traces = [t_ for t_ in self.traces if t_["id"] != tr["id"]]
                    self.traces.append(dict(tr, lieu=x["lieu"], piece=x["piece"], depuis=maintenant, source=x["_n"],
                                            jusqu=maintenant + tr["heures"] * 12 if tr.get("heures") else None))
            fuite = self.fuite.get(x["lieu"])
            if x.get("_ok") and fuite and fuite[0] == q.date and d <= i < f and fuite[1] < maintenant:
                x["_ok"] = False
                self.echecs.append(f"{q.date} {hm(i)} : {g['nom']} interrompu, le voyageur s'enfuit")
                continue
            if i == f - 1 and x.get("_ok"):
                eff = self.FATIGUE["efficacite"] if x.get("_fatigue") else 1.0   # fatigué, il travaille moins bien
                self.finis[x["geste"]] = maintenant + 1
                self.avancement.update(g.get("fait", {}))
                if "creuse_m_par_heure" in g:
                    self.avancement["profondeur_m"] = round(self.avancement.get("profondeur_m", 0) + self.duree(x) / 60 * g["creuse_m_par_heure"] * eff, 2)
                    if self.avancement["profondeur_m"] >= g["trouve_a_m"] and self.avancement.get("branche") is None:
                        self.avancement.update(g["trouve"])
                        self.noter(q, i, f"trouve la branche fossilisée, à {self.avancement['profondeur_m']} m")
                for t_ in self.traces:
                    if t_["id"] in g.get("efface", []) and (t_["jusqu"] is None or t_["jusqu"] > maintenant):
                        if eff < 1:
                            t_["visibilite"] = round(t_["visibilite"] * (1 - eff), 3)
                        else:
                            t_["jusqu"] = maintenant
                    if t_["id"] in g.get("attenue", {}):
                        t_["visibilite"] = round(t_["visibilite"] * (1 - (1 - g["attenue"][t_["id"]]) * eff), 3)

    def vu_entendu(self, q, i):
        """Pendant un geste : qui est dans la pièce voit le voyageur au travail, qui est ailleurs dans le lieu l'entend."""
        for x in self.I:
            place = self.ou_est_il(q, x, i) if x["type"] == "geste" and x.get("_ok") else None
            if not place:
                continue
            g, (endroit, _) = self.G[x["geste"]], place
            for pid, h in q.H.items():
                if h.attente[1]["mode"] == "sommeil":
                    continue
                ici = q.ou(pid, h)
                if ici == endroit and g.get("vu"):
                    self.remarquer(q, pid, h, i, f"vu:{x['geste']}", g["vu"]["remarque"], g["vu"]["visibilite"], True, x["_n"],
                                   genre="vu", lieu=x["lieu"], piece=x["piece"])
                elif ici[0] == endroit[0] and g.get("bruit"):
                    self.remarquer(q, pid, h, i, f"bruit:{x['geste']}", g["bruit"]["remarque"], g["bruit"]["visibilite"], False, x["_n"],
                                   genre="bruit", lieu=x["lieu"], piece=x["piece"])
            self.voisins(q, x, g, i)
        self.reagir_aux_signalements(q, i)

    # ------------------------------------------------------------ voisins
    def voisins(self, q, x, g, i):
        """Les voisins du lieu (data/monde/voisinages.json) : qui est dans leur logement entend le geste à travers le
        plancher, éveillé ou réveillé, selon son ouïe ; depuis la pièce qui a vue sur le lieu, il peut voir certains gestes."""
        V = self.VOISINS.get(x["lieu"])
        if not V:
            return
        for pid, h in q.H.items():
            ici = q.ou(pid, h)
            if ici[0] != V["logement"]:
                continue
            dort = h.attente[1]["mode"] == "sommeil"
            sante = q.fiches[pid].get("sante", {})
            if g.get("bruit"):
                vis = g["bruit"]["visibilite"] * V.get("plancher", 1.0) * self.ouie(h, sante)
                quoi = g["bruit"]["remarque"]
                if dort:
                    vis *= sante.get("sommeil", {}).get("reveil_au_bruit", 0.3)
                    quoi += ", qui " + ("la" if q.fiches[pid]["identite"].get("genre") == "femme" else "le") + " réveille"
                self.remarquer(q, pid, h, i, f"bruit:{x['geste']}", quoi, vis, False, x["_n"], genre="bruit", lieu=x["lieu"], piece=x["piece"])
            vue = V.get("vue")
            if vue and not dort and ici[1] == vue["piece"] and x["geste"] in vue["gestes"]:
                eph = q.fiches[pid]["meta"].get("ephemerides_lyon_approximatives", {}).get(q.date, {})
                jour = eph and idx(eph["lever_soleil"]) <= i < idx(eph["coucher_soleil"])
                self.remarquer(q, pid, h, i, f"vu:{x['geste']}", vue["remarque"], vue["visibilite"] * (1 if jour else vue.get("de_nuit", 1)),
                               False, x["_n"], genre="vu", lieu=x["lieu"], piece=x["piece"])

    @staticmethod
    def ouie(h, sante):
        """Ce qu'il entend d'un bruit (sante.audition) : avec l'objet qui le fait entendre porté sur lui, ou sans."""
        A = sante.get("audition")
        if not A:
            return 1.0
        o = next((o for o in h.fiche["objets"] if o["id"] == A["objet"]), None)
        porte = o and h.sim.positions.get(o["id"]) == (o.get("positions") or {}).get("porte")
        return A["avec"] if porte else A["sans"]

    def signaler(self, q, pid, anomalie, i):
        """On vient de lui raconter ce qu'un voisin a remarqué chez lui (quartier.py) : il y réagira la prochaine fois qu'il
        y sera, comme s'il l'avait remarqué lui-même."""
        if anomalie.get("lieu") and self.chez_lui(q.fiches[pid], anomalie["lieu"]):
            self.signalements.append(dict(anomalie, a=pid, instant=self.instant(q.date, i)))

    def reagir_aux_signalements(self, q, i):
        maintenant = self.instant(q.date, i)
        for e in list(self.signalements):
            h = q.H.get(e["a"])
            if not h or e["instant"] >= maintenant or h.attente[1]["mode"] == "sommeil" or q.ou(e["a"], h)[0] != e["lieu"]:
                continue
            self.signalements.remove(e)
            self.noter(q, i, f"{q.prenom(e['a'])} a appris de {q.prenom(e['par'])} : {e['quoi']}")
            self.reagir(q, e["a"], h, i, e["genre"], e["objet"], e["lieu"], e["piece"])

    def traces_remarquees(self, q, i):
        """Les traces qui restent : qui est dans la pièce (ou dans le lieu, pour une odeur, une poussière) peut les remarquer."""
        maintenant = self.instant(q.date, i)
        for tr in self.traces:
            if tr["depuis"] > maintenant or (tr["jusqu"] is not None and tr["jusqu"] <= maintenant) or not tr["visibilite"]:
                continue
            for pid, h in q.H.items():
                if h.attente[1]["mode"] == "sommeil":
                    continue
                ici = q.ou(pid, h)
                if ici == (tr["lieu"], tr["piece"]) or (tr["portee"] == "lieu" and ici[0] == tr["lieu"]):
                    self.remarquer(q, pid, h, i, f"trace:{tr['id']}", tr["remarque"], tr["visibilite"], False, tr["source"],
                                   genre="trace", lieu=tr["lieu"], piece=tr["piece"])

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
        if x.get("explique"):
            # ce qu'on lui annonce ne l'étonnera plus
            h.mem.setdefault("explications", []).extend(g for g in x["explique"] if g not in h.mem["explications"])
        if x.get("explique") and x.get("lieu"):   # une annonce qui ne concerne personne d'autre ne vaut pas d'être racontée
            h.mem.setdefault("anomalies", []).append({"date": q.date, "heure": hm(i), "objet": f"annonce:{zlib.crc32(x['quoi'].encode()):08x}", "source": f"V{x['_n']}",
                                                      "quoi": f"un ouvrier lui a annoncé : « {x['quoi']} »", "explique": list(x["explique"])}
                                                     | {"genre": "bruit", "lieu": x["lieu"], "piece": x.get("piece", x["lieu"])})
