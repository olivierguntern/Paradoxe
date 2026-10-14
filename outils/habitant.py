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

La nuit s'enchaîne d'elle-même : l'étape « coucher » éteint, l'endormissement
dure selon l'anxiété et l'excitation, puis le sommeil va jusqu'à la première
étape du lendemain.
"""
import datetime

from agent import JOURS, phase_sommeil
from moteur import PAS_PAR_JOUR, Journee, Simulation, hm, idx


class Habitant:
    def __init__(self, fiche, catalogue, date, etat):
        self.fiche = fiche
        self.A = catalogue["actions"]
        self.date = date
        self.jour = JOURS[datetime.date.fromisoformat(date).weekday()]
        self.sim = Simulation(fiche, date, etat)
        self.PIECES = fiche["domicile"]["pieces"]
        self.SEUILS = {n: b["seuil_alerte"] for n, b in fiche["besoins"].items()}
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
        self.opportunites = {}   # début d'étape -> besoins satisfaits en s'y mettant

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

    def piece_pour(self, mot):
        """Première pièce du logement dont l'identifiant, le nom ou le mobilier contient le mot."""
        m = mot.lower()
        for pc in self.PIECES:
            if m == pc["id"] or m in pc["nom"].lower() or any(m in x.lower() for x in pc["mobilier"]):
                return pc["id"]
        return None

    @property
    def i(self):
        return len(self.sim.steps)

    # ------------------------------------------------------------ décision
    def etape(self, i):
        return next(((d, f, e, r) for d, f, e, r in self.etapes if d <= i < f), None)

    def resoudre(self, d, f, e, i):
        """Action de l'étape au pas i : phase en cours et variantes selon les besoins."""
        a = dict(self.A[e["activite"]])
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
        return a, (d, phase), debut

    def utilite(self, a, d, f, i):
        """Scores des actions possibles : l'ancrage vaut 1 ; un besoin pressant (sous son seuil d'alerte) peut
        l'emporter à tout moment ; au début d'une étape, un besoin simplement inconfortable (sous le double de
        son seuil) aussi, avec un score moindre : il en profite avant de s'y mettre."""
        scores = [(1.0, None)]
        if a.get("ininterrompable") or f - i <= 2:
            return scores
        transition = i == d + self.opportunites.get(d, 0)
        for besoin, aid in self.BESOINS.items():
            v, s = self.sim.besoins[besoin], self.SEUILS[besoin]
            if besoin in a.get("effets", {}):
                continue
            if v < s:
                scores.append((1 + (s - v) / s, aid))
            elif transition and v < 2 * s:
                scores.append((1 + 0.5 * (2 * s - v) / (2 * s), aid))
        return sorted(scores, key=lambda x: -x[0])

    # ------------------------------------------------------------ émission
    def emettre(self, a, titre, routine, piece, premier, avec=(), garder_appareils=False):
        st = {"action": a["texte"], "pensee": None, "piece": piece, "lieu": "domicile", "mode": a.get("mode", "eveille"),
              "charge": a.get("charge", "simple"), "posture": a.get("posture", "debout")}
        if a.get("exterieur"):
            st["lieu"] = "exterieur"
        if premier:
            if a.get("effets"):
                st["effets"] = dict(a["effets"])
            if a.get("ev"):
                st["ev"] = list(a["ev"])
        voulus = set(self.allumes) if garder_appareils else set(a.get("appareils", [])) | set(avec)
        app = {"allume": sorted(voulus - self.allumes), "eteint": sorted(self.allumes - voulus)}
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

    def pousser(self, st, titre, routine):
        s = {"titre": titre, "routine": routine, "piece": st.pop("piece"), "lieu": st.pop("lieu"), "mode": st.pop("mode"),
             "charge": st.pop("charge"), "posture": st.pop("posture")}
        entree = self.sim.pas(st, s)
        segs = self.j.segments
        if segs and segs[-1]["titre"] == titre and segs[-1]["routine"] == routine:
            segs[-1]["pas"].append(st)
        else:
            segs.append({"debut": hm(entree["pas"]), "titre": titre, "routine": routine, "pas": [st]})
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
        self.pousser(st, titre, "sommeil")

    # ------------------------------------------------------------ journée
    def vivre(self):
        veille = JOURS[(JOURS.index(self.jour) - 1) % 7]
        while self.i < PAS_PAR_JOUR:
            i = self.i
            if self.coucher and i >= self.coucher[1]:
                self.dormir("Sommeil")
                continue
            et = self.etape(i)
            if et is None:
                self.dormir(f"Nuit de {veille} à {self.jour}")
                continue
            d, f, e, r = et
            a, cle, debut = self.resoudre(d, f, e, i)
            if a.get("sommeil"):
                self.endormir(a, e, r)
                continue
            score, besoin = self.utilite(a, d, f, i)[0]
            if besoin:
                b = self.A[besoin]
                piece = self.piece_pour(b["lieu"])
                v = round(self.sim.besoins[b["besoin"]], 1)
                if v < self.SEUILS[b["besoin"]]:
                    self.decisions.append(f"{hm(i)} : {b['besoin']} sous le seuil d'alerte ({v}, score {round(score, 2)}) ; interrompt « {e['action']} ».")
                    self.emettre(b, "Besoin pressant", "interruption", piece, True, garder_appareils=True)
                else:
                    self.opportunites[d] = self.opportunites.get(d, 0) + 1
                    self.emettre(dict(b, texte=b["texte"].replace("S'interrompt pour", "Avant de s'y mettre,")), e["action"], r, piece, True,
                                 garder_appareils=True)
                continue
            if a.get("exterieur"):
                piece = e["lieu"]
            elif a.get("lieu_phase"):
                piece = self.piece_pour(a["lieu_phase"]) or e["lieu"]
            elif e["lieu"] in self.sim.PIECES:
                piece = e["lieu"]
            else:
                piece = self.piece_pour(a["lieu"]) or self.sim.piece
            premier = cle not in self.faits
            self.faits.add(cle)
            self.emettre(a, e["action"], r, piece, premier, avec=e.get("avec", ()))
        return self.terminer()

    def endormir(self, a, e, r):
        """Étape du coucher : il éteint ; l'endormissement dure selon son état ; puis il dort jusqu'au lendemain."""
        lit = self.piece_pour(a["lieu"])
        st = {"action": a["texte"], "pensee": None, "piece": lit, "lieu": "domicile", "mode": "eveille", "charge": "repos", "posture": "allongé"}
        eteint = sorted(self.allumes) + ([f"lumiere-{lit}"] if self.sim.lumieres.get(lit) else [])
        if eteint:
            st["app"] = {"eteint": eteint}
        self.allumes = set()
        entree = self.pousser(st, e["action"], r)
        latence = self.sim.latence_endormissement(entree["emotions"])
        self.j.extinction, self.j.endormissement = entree["heure"], latence
        self.coucher = (entree["pas"], entree["pas"] + latence // 5)
        self.mem["endormi_a"] = self.coucher[1] - PAS_PAR_JOUR
        for _ in range(latence // 5 - 1):
            self.pousser({"action": "Cherche le sommeil.", "pensee": None, "piece": lit, "lieu": "domicile", "mode": "eveille",
                          "charge": "repos", "posture": "allongé"}, "Endormissement", r)

    def terminer(self):
        etat_final, stats = self.sim.terminer(self.j.extinction, self.j.endormissement)
        etat_final["habitant"] = self.mem
        self.j.ecarts = self.decisions
        self.j.bilan = ["Journée vécue par l'habitant générique."]
        return self.sim.steps, etat_final, stats
