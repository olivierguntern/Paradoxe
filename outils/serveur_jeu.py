"""Serveur local du jeu : jouer John depuis le navigateur.

Usage : python3 outils/serveur_jeu.py [--port 8010]
puis ouvrir http://127.0.0.1:8010/jouer.html

Sert les pages de vue/ et trois appels :
- GET  /api/catalogue : la mission, les gestes, les objets de l'époque, les
  habitants (et leurs objets), les jours, et les scénarios existants (pour partir d'un plan) ;
- POST /api/simuler   : un plan de John (le scénario, au format de
  data/voyageur/<nom>.json) ; le quartier est rejoué avec lui, la divergence
  mesurée et la mission évaluée ; renvoie le résultat ;
- GET  /api/partie    : la dernière partie, au format de la page du voyageur
  (vue/divergence.html?partie l'affiche avec sa frise et sa chaîne des causes) ;
- GET  /api/sims      : la dernière partie, au format de la vue façon Sims
  (vue/sims.html la charge après chaque action de John).

Les jours qui précèdent la première intervention sont ceux du monde de
référence (data/quartier), recopiés plutôt que simulés. La partie est écrite
dans data/voyageur/parties/ (non versionné). Le serveur n'écoute que sur la
machine elle-même (127.0.0.1).
"""
import argparse
import gzip
import http.server
import json
import os
import shutil
import sys
import threading
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from divergence import comparer_mondes
from exporter_divergence import Textes, etat, journees, scenario_page
from exporter_sims import construire as construire_sims
from fiches import MONDE, lire
from simuler_quartier import simuler
from simuler_voyageur import evaluer_mission
from voyageur import Voyageur

sys.stdout.reconfigure(encoding="utf-8")
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VUE = os.path.join(RACINE, "vue")
REFERENCE = os.path.join(RACINE, "data", "quartier")
PARTIES = os.path.join(RACINE, "data", "voyageur", "parties")


class Jeu:
    def __init__(self):
        self.habitants = sorted(d for d in os.listdir(REFERENCE) if os.path.isdir(os.path.join(REFERENCE, d)))
        self.dates = sorted(f[:-5] for f in os.listdir(os.path.join(REFERENCE, self.habitants[0])) if f.endswith(".json"))
        self.ref = {p: [etat(s) for J in journees(REFERENCE, p, self.dates) for s in J["pas"]] for p in self.habitants}
        # la table des textes de la page du voyageur : la partie y ajoute les siens à la suite
        t = open(os.path.join(VUE, "divergence.js"), encoding="utf-8").read()
        self.base = json.loads(t[t.index("{"):t.rindex("}") + 1])["textes"]
        self.partie = None
        self.sims = None
        self.verrou = threading.Lock()   # une partie à la fois

    def catalogue(self):
        fiches = {p: lire(os.path.join(RACINE, "data", "personnages", f"{p}.json")) for p in self.habitants}
        scenarios = []
        for f in sorted(os.listdir(os.path.join(RACINE, "data", "voyageur"))):
            if f.endswith(".json"):
                sc = lire(os.path.join(RACINE, "data", "voyageur", f))
                scenarios.append({"id": f[:-5], "description": sc.get("description", ""), "mission": sc.get("mission"),
                                  "porte": sc.get("porte", []), "interventions": sc["interventions"]})
        missions = {f[:-5]: lire(os.path.join(RACINE, "data", "missions", f)) for f in os.listdir(os.path.join(RACINE, "data", "missions")) if f.endswith(".json")}
        return {"dates": self.dates, "habitants": [{"id": p, "prenom": fiches[p]["identite"]["prenom"],
                                                    "objets": [[o["id"], o["nom"]] for o in fiches[p].get("objets", [])]} for p in self.habitants],
                "gestes": lire(os.path.join(MONDE, "gestes.json"))["gestes"], "epoque": lire(os.path.join(MONDE, "epoque.json")),
                "missions": missions, "scenarios": scenarios}

    def simuler(self, sc):
        """Rejoue le quartier avec le plan de John ; renvoie le résultat et prépare la partie pour la page du voyageur."""
        with self.verrou:
            return self._simuler(sc)

    def _simuler(self, sc):
        for x in sc["interventions"]:
            x.pop("_n", None)
        v = Voyageur(sc)   # vérifie le plan (gestes connus, pas de geste qui passe minuit)
        dossier = os.path.join(PARTIES, "partie")
        if os.path.isdir(dossier):
            shutil.rmtree(dossier)
        premiere = min((x["date"] for x in sc["interventions"]), default=self.dates[-1])
        for p in self.habitants:
            os.makedirs(os.path.join(dossier, p), exist_ok=True)
            for d in self.dates:
                if d < premiere:   # avant le voyageur : le monde de référence, tel quel
                    for ext in (".json", ".md"):
                        shutil.copy(os.path.join(REFERENCE, p, d + ext), os.path.join(dossier, p, d + ext))
        json.dump(sc, open(os.path.join(PARTIES, "partie.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        simuler(self.habitants, premiere, self.dates[-1], dossier, v, bavard=False)
        for x in sc["interventions"]:
            if x["type"] == "geste":
                x["_duree"] = v.duree(x)
        r = comparer_mondes(REFERENCE, dossier, v.cibles(), sc["interventions"])
        if sc.get("mission"):
            r["mission"] = evaluer_mission(sc["mission"], v, r["verdict"])
        r["voyageur"] = [{"date": d, "heure": h, "action": t} for d, h, t in v.journal]
        T = Textes()
        for x in self.base:
            T(x)
        page = scenario_page("partie", sc, r, dossier, self.habitants, self.dates, self.ref, T)
        self.partie = {"scenario": page, "base": len(self.base), "textes": T.liste[len(self.base):]}
        self.sims = construire_sims(dossier)
        self.sims["voyageur"] = [{k: v for k, v in x.items() if not k.startswith("_") or k == "_duree"} for x in sc["interventions"]]
        res = {"verdict": r["verdict"], "mission": r.get("mission"), "voyageur": r["voyageur"], "touches": r["touches"],
               "cascade": r["cascade"], "faits": len(r["causes"]["faits"]), "arbre": r["arbre"]}
        self.sims["resultat"] = res
        return res


class Gestionnaire(http.server.SimpleHTTPRequestHandler):
    jeu = None
    # types fixés ici : sous Windows, ceux du registre peuvent faire refuser les scripts par le navigateur
    extensions_map = {"": "application/octet-stream", ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                      ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml"}

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=VUE, **kw)

    def repondre(self, code, obj):
        corps = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        gz = "gzip" in self.headers.get("Accept-Encoding", "") and len(corps) > 4096
        if gz:   # les données de la vue du quartier font plus d'un mégaoctet : compressées, six fois moins
            corps = gzip.compress(corps, 6)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        for k in range(0, len(corps), 65536):   # par morceaux : sous Windows, un seul envoi d'un gros bloc peut être coupé
            self.wfile.write(corps[k:k + 65536])

    def do_GET(self):
        if self.path in ("/", "/index"):
            self.send_response(302)
            self.send_header("Location", "/jouer.html")
            self.end_headers()
        elif self.path.startswith("/api/catalogue"):
            self.repondre(200, self.jeu.catalogue())
        elif self.path.startswith("/api/partie"):
            self.repondre(200, self.jeu.partie or {})
        elif self.path.startswith("/api/sims"):
            self.repondre(200, self.jeu.sims or {})
        else:
            super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/api/simuler"):
            self.repondre(404, {"erreur": "inconnu"})
            return
        try:
            sc = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
            print(f"partie : {len(sc.get('interventions', []))} intervention(s)…", flush=True)
            res = self.jeu.simuler(sc)
            print(f"  {res['verdict']}" + (f" — mission {res['mission']['resultat']}" if res.get("mission") else ""), flush=True)
            self.repondre(200, res)
        except (ValueError, KeyError) as e:
            self.repondre(400, {"erreur": str(e)})
        except Exception as e:
            traceback.print_exc()
            self.repondre(500, {"erreur": f"{type(e).__name__} : {e}"})

    def log_message(self, fmt, *args):
        if "/api/" in str(args[0] if args else ""):
            super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8010)
    a = ap.parse_args()
    Gestionnaire.jeu = Jeu()
    serveur = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), Gestionnaire)
    print(f"Paradoxe : http://127.0.0.1:{a.port}/jouer.html (Ctrl+C pour arrêter)", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
