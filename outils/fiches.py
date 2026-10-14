"""Chargement des fiches d'habitants.

Une fiche ne décrit que ce qui est propre au personnage : identité,
personnalité, routines, relations, objets, ce qui le distingue. Le reste vient
du monde (data/monde/) :
- humain.json : besoins, modèle émotionnel et catalogue d'événements communs,
  sommeil, état initial, valeurs par défaut de toute fiche ;
- calendrier.json : période simulée et éphémérides ;
- lieux.json : lieux publics ;
- logements/<id>.json : logements partagés, cités par la fiche dans
  `logements` (le premier est chez lui ; les autres, où il va en visite, ont
  leurs pièces préfixées « logement:pièce »).

Une valeur de la fiche l'emporte toujours ; les fiches complètes (Thomas,
Robert) se chargent donc à l'identique, seulement complétées de ce qui leur
manque.
"""
import copy
import json
import os

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONDE = os.path.join(RACINE, "data", "monde")


def lire(chemin):
    return json.load(open(chemin, encoding="utf-8"))


def completer(d, defauts):
    """Ajoute à d ce qui manque de defauts, récursivement (dictionnaires seulement) ; une valeur de d l'emporte."""
    for k, v in defauts.items():
        if k not in d:
            d[k] = copy.deepcopy(v)
        elif isinstance(d[k], dict) and isinstance(v, dict):
            completer(d[k], v)
    return d


def logement(lid):
    return lire(os.path.join(MONDE, "logements", f"{lid}.json"))


def domicile_depuis_logements(f):
    """Construit domicile, plan et lieux de la fiche à partir des logements qu'elle cite."""
    pieces, liaisons, noeuds, entrees, acces, lieux = [], [], [], {}, {}, []
    immeuble, equipements = None, {}
    for k, ref in enumerate(f["logements"]):
        lid = ref if isinstance(ref, str) else ref["id"]
        L = logement(lid)
        pre = "" if k == 0 else f"{lid}:"
        for p in L["pieces"]:
            pieces.append(dict(p, id=pre + p["id"], lieu=lid, logement=lid, id_local=p["id"]))
        liaisons += [dict(x, a=pre + x["a"], b=pre + x["b"]) for x in L["liaisons"]]
        noeuds += [pre + n for n in L["noeuds_exterieurs"]]
        entrees[lid], acces[lid] = pre + L["entree"], pre + L["acces"]
        lieux.append({"id": lid, "nom": L["nom"], "type": L["type"], "adresse": L.get("adresse", "")})
        if k == 0:
            immeuble, equipements = L.get("escalier"), L.get("equipements", {})
    dom = f.setdefault("domicile", {})
    dom.update(lieu_id="domicile", pieces=pieces)
    dom.setdefault("equipements", equipements)
    plan = dom.setdefault("plan", {})
    plan.update(liaisons=liaisons, noeuds_exterieurs=noeuds, entrees=entrees, acces=acces,
                lieux_des_sites={lid: lid for lid in entrees}, logements_des_sites={lid: lid for lid in entrees})
    if immeuble and "immeuble" not in f:
        f["immeuble"] = immeuble
    f.setdefault("lieux", [])
    f["lieux"] += [l for l in lieux if l["id"] not in {x["id"] for x in f["lieux"]}]


def charger(pid):
    return completer_fiche(lire(os.path.join(RACINE, "data", "personnages", f"{pid}.json")), pid)


def completer_fiche(f, pid=None):
    if f.get("logements"):
        domicile_depuis_logements(f)
    cal = lire(os.path.join(MONDE, "calendrier.json"))
    meta = f.setdefault("meta", {})
    meta.setdefault("id", pid)
    meta.setdefault("version", 1)
    for k in ("periode", "echelles", "ephemerides_lyon_approximatives"):
        meta.setdefault(k, cal[k])
    completer(f, lire(os.path.join(MONDE, "humain.json")))
    connus = {x["id"] for x in f.setdefault("lieux", [])}
    if "domicile" not in connus:
        f["lieux"].append({"id": "domicile", "nom": "Chez lui", "type": "logement"})
    f["lieux"] += [l for l in lire(os.path.join(MONDE, "lieux.json"))["lieux"] if l["id"] not in connus]
    ei = f["etat_initial"]
    if "piece" not in ei:
        ei["piece"] = next(p["id"] for p in f["domicile"]["pieces"] if any("lit" in m.lower().split() for m in p["mobilier"]))
    return f
