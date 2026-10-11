"""Moteur de calcul des journées de Paradoxe.

Le contenu d'une journée (actions, pensées, rêves, événements vécus, objets,
appareils) est rédigé dans outils/journees/<date>.py. Ce moteur calcule, avec
les règles de la fiche du personnage : déplacements, lumière, besoins,
émotions et concentration. Il vérifie aussi que chaque objet déplacé se
trouvait bien là où la journée le prend, d'un jour à l'autre.
"""
import heapq
import json

PAS_PAR_JOUR = 288


# ---------------------------------------------------------------- temps
def hm(i):
    m = i * 5
    return f"{m // 60:02d}:{m % 60:02d}"


def idx(h):
    a, b = map(int, h.split(":"))
    return (a * 60 + b) // 5


# ---------------------------------------------------------------- rédaction
def p(action, pensee=None, **kw):
    """Un pas de 5 minutes. Options : ev, objets, consommation, effets, app,
    radio, musique, mode, charge, posture, piece, lieu, via, via_apres, sortie,
    retour, escalier, parcours, phase_sommeil, reve."""
    d = {"action": action, "pensee": pensee}
    d.update(kw)
    return d


def mv(objet, de, vers):
    return {"objet": objet, "de": de, "vers": vers}


def on(*a):
    return {"allume": list(a)}


def off(*a):
    return {"eteint": list(a)}


def onoff(allume=(), eteint=()):
    return {"allume": list(allume), "eteint": list(eteint)}


def course(distance_m, denivele_m=0):
    return {"moyen": "course", "distance_m": distance_m, "denivele_m": denivele_m}


def marche(distance_m, denivele_m=0):
    return {"moyen": "marche", "distance_m": distance_m, "denivele_m": denivele_m}


class Journee:
    def __init__(self, date, jour, extinction):
        self.date = date
        self.jour = jour
        self.extinction = extinction  # heure où il éteint pour dormir
        self.segments = []
        self.ecarts = []
        self.bilan = []
        self.resume = {}

    def seg(self, debut, titre, piece, routine, mode, charge, posture, pas, lieu="domicile"):
        self.segments.append(dict(debut=debut, titre=titre, piece=piece, routine=routine, mode=mode,
                                  charge=charge, posture=posture, pas=pas, lieu=lieu))


# ---------------------------------------------------------------- état
def etat_initial_depuis_fiche(fiche):
    positions = {}
    for o in fiche["objets"]:
        e = o["emplacement_initial"]
        positions[o["id"]] = f"{e['piece']} / {e['support']}" if e["lieu"] == "domicile" else f"{e['lieu']} / {e['piece']} / {e['support']}"
    emo = dict(fiche["etat_initial"]["emotions"])
    conc = emo.pop("concentration")
    return {"piece": fiche["etat_initial"]["piece"], "besoins": dict(fiche["etat_initial"]["besoins"]),
            "emotions": emo, "concentration": conc, "lumieres": {}, "appareils": [], "positions": positions, "cafe": []}


def etat_depuis_veille(chemin_json):
    return json.load(open(chemin_json))["etat_final"]


# ---------------------------------------------------------------- simulation
class Incoherence(Exception):
    pass


def simuler(fiche, j, etat):
    B = fiche["besoins"]
    M = fiche["modele_emotionnel"]
    EV = M["evenements"]
    NEVRO = fiche["personnalite"]["big_five"]["nevrosisme"]
    PIECES = {pc["id"]: pc for pc in fiche["domicile"]["pieces"]}
    PLAN = fiche["domicile"]["plan"]
    IMM = fiche["immeuble"]
    eph = fiche["meta"]["ephemerides_lyon_approximatives"][j.date]
    LEVER, COUCHER = idx(eph["lever_soleil"]), idx(eph["coucher_soleil"])
    HL = M["demi_vie_pas"]
    CIBLES = M["concentration"]["cibles"]
    DP = PLAN["deplacements_dans_la_piece"]

    graph = {}
    for l in PLAN["liaisons"]:
        graph.setdefault(l["a"], []).append((l["b"], l["distance_m"]))
        graph.setdefault(l["b"], []).append((l["a"], l["distance_m"]))

    def chemin(a, b):
        dist, prev, q = {a: 0}, {}, [(0, a)]
        while q:
            d, u = heapq.heappop(q)
            if u == b:
                break
            for v, w in graph[u]:
                if d + w < dist.get(v, 1e9):
                    dist[v], prev[v] = d + w, u
                    heapq.heappush(q, (d + w, v))
        path = [b]
        while path[-1] != a:
            path.append(prev[path[-1]])
        return path[::-1], dist[b]

    def besoin_lumiere(piece, i):
        return piece in PIECES and (not PIECES[piece]["fenetre"] or i < LEVER or i >= COUCHER)

    def negatif(e, d):
        return (d > 0 and e in ("tristesse", "anxiete", "colere", "solitude")) or (d < 0 and e in ("joie", "fierte"))

    def clamp(v, hi=100.0):
        return max(0.0, min(hi, v))

    besoins = dict(etat["besoins"])
    emo = dict(etat["emotions"])
    conc = etat["concentration"]
    lumieres = {pc: bool(etat["lumieres"].get(pc)) for pc in PIECES}
    appareils = set(etat["appareils"])
    positions = dict(etat["positions"])
    cafe = list(etat["cafe"])
    base = {k: v for k, v in M["etat_de_base"].items() if k != "solitude"}
    piece_prec = etat["piece"]
    st_ = {"entre_pieces_m": 0.0, "dans_les_pieces_m": 0.0, "exterieur_m": 0.0, "foulees": 0.0,
           "passages_de_piece": 0, "marches": 0, "denivele_positif_m": 0, "denivele_negatif_m": 0, "lumiere_allumages": 0}
    steps = []
    attendu = 0

    for s in j.segments:
        if idx(s["debut"]) != attendu:
            raise Incoherence(f"segment « {s['titre']} » commence à {s['debut']} au lieu de {hm(attendu)}")
        for k, st in enumerate(s["pas"]):
            i = attendu + k
            piece = st.get("piece", s["piece"])
            lieu = st.get("lieu", s["lieu"])
            mode = st.get("mode", s["mode"])
            charge = st.get("charge", s["charge"])
            posture = st.get("posture", s["posture"])
            radio = st.get("radio", False)
            endormi = mode == "sommeil"
            lum = []

            # ---- déplacements dans l'appartement
            depart = piece_prec
            arrivee = piece
            if st.get("sortie"):
                arrivee = "palier"
            if st.get("retour"):
                depart = "palier"
            etapes = [depart] + st.get("via", []) + [arrivee] + st.get("via_apres", [])
            if st.get("via_apres"):
                etapes.append(arrivee)
            parcours_app = [depart]
            dist = 0.0
            for a, b in zip(etapes, etapes[1:]):
                if a == b or a not in graph or b not in graph:
                    continue
                pth, d = chemin(a, b)
                parcours_app += pth[1:]
                dist += d
            dep = {}
            if len(parcours_app) > 1:
                dep.update({"chemin": parcours_app, "distance_m": round(dist, 1),
                            "duree_s": round(dist / PLAN["vitesse_marche_m_s"]),
                            "foulees": round(dist / PLAN["longueur_foulee_m"])})
                st_["entre_pieces_m"] += dist
                st_["foulees"] += dist / PLAN["longueur_foulee_m"]
                st_["passages_de_piece"] += len(parcours_app) - 1
                aller_retour = parcours_app[-1] == parcours_app[0]
                for a, b in zip(parcours_app, parcours_app[1:]):
                    if lumieres.get(a) and not (aller_retour and a == parcours_app[0]):
                        lumieres[a] = False
                        lum.append(f"éteint la lumière ({a})")
                    if besoin_lumiere(b, i) and not lumieres[b] and not (aller_retour and b == parcours_app[0]):
                        lumieres[b] = True
                        st_["lumiere_allumages"] += 1
                        lum.append(f"allume la lumière ({b})")
            elif not endormi and i == COUCHER and besoin_lumiere(piece, i) and not lumieres[piece]:
                lumieres[piece] = True
                st_["lumiere_allumages"] += 1
                lum.append(f"allume la lumière ({piece}) : la nuit tombe")

            # ---- escalier et parcours extérieur
            effets_escalier = {}
            if "escalier" in st:
                sens = st["escalier"]["sens"]
                dimm = IMM["deplacement"]
                duree = dimm["descente_secondes"] if sens == "descente" else (
                    dimm["montee_secondes_apres_course"] if st["escalier"].get("apres_course") else dimm["montee_secondes_marche"])
                dep["escalier"] = {"sens": sens, "etages": IMM["etage_appartement"], "marches": IMM["marches_total"], "duree_s": duree}
                st_["marches"] += IMM["marches_total"]
                st_["foulees"] += IMM["marches_total"]
                effets_escalier = dimm["effets_descente"] if sens == "descente" else dimm["effets_montee"]
            if "parcours" in st:
                dep["parcours"] = st["parcours"]
                for seg_ in st["parcours"]:
                    st_["exterieur_m"] += seg_["distance_m"]
                    st_["foulees"] += seg_["distance_m"] / (PLAN["longueur_foulee_course_m"] if seg_["moyen"] == "course" else PLAN["longueur_foulee_m"])
                    if seg_["denivele_m"] > 0:
                        st_["denivele_positif_m"] += seg_["denivele_m"]
                    else:
                        st_["denivele_negatif_m"] += -seg_["denivele_m"]
                dep["foulees_exterieur"] = round(sum(
                    x["distance_m"] / (PLAN["longueur_foulee_course_m"] if x["moyen"] == "course" else PLAN["longueur_foulee_m"])
                    for x in st["parcours"]))

            # ---- appareils et lumières commandés explicitement
            for a in st.get("app", {}).get("allume", []):
                if a.startswith("lumiere-"):
                    if not lumieres[a[8:]]:
                        lumieres[a[8:]] = True
                        st_["lumiere_allumages"] += 1
                        lum.append(f"allume la lumière ({a[8:]})")
                else:
                    appareils.add(a)
            for a in st.get("app", {}).get("eteint", []):
                if a.startswith("lumiere-"):
                    if lumieres[a[8:]]:
                        lumieres[a[8:]] = False
                        lum.append(f"éteint la lumière ({a[8:]})")
                else:
                    appareils.discard(a)
            piece_prec = piece

            # ---- petits déplacements dans la pièce
            if piece in PIECES:
                intra = DP["metres_par_pas"][charge] * (DP["facteur_assis_ou_allonge"] if posture in ("assis", "allongé") else 1.0)
                st_["dans_les_pieces_m"] += intra
                st_["foulees"] += intra / PLAN["longueur_foulee_m"]

            # ---- objets : chaque déplacement doit partir de la position connue
            for o in st.get("objets", []):
                if o["objet"] not in positions:
                    raise Incoherence(f"{hm(i)} : objet inconnu {o['objet']}")
                if positions[o["objet"]] != o["de"]:
                    raise Incoherence(f"{hm(i)} : {o['objet']} est à « {positions[o['objet']]} », pas à « {o['de']} »")
                positions[o["objet"]] = o["vers"]

            # ---- besoins
            def var(n, cle):
                return B[n]["variation_par_pas"].get(cle, B[n]["variation_par_pas"]["eveille"])
            if endormi:
                for n in ("faim", "soif", "energie", "hygiene", "toilettes"):
                    besoins[n] += B[n]["variation_par_pas"]["endormi"]
            else:
                effort = mode == "effort"
                besoins["faim"] += var("faim", "effort_physique" if effort else "eveille")
                besoins["soif"] += var("soif", "effort_physique" if effort else "eveille")
                besoins["energie"] += B["energie"]["variation_par_pas"]["sieste" if mode == "sieste" else ("effort_physique" if effort else "eveille")]
                besoins["hygiene"] += var("hygiene", "effort_physique" if effort else "eveille")
                besoins["toilettes"] += B["toilettes"]["variation_par_pas"]["eveille"]
                if mode != "sieste":
                    besoins["social"] += B["social"]["variation_par_pas"]["eveille"] + (B["social"]["satisfaction"]["radio_par_pas"] if radio else 0)
                    if mode == "travail":
                        besoins["detente"] += B["detente"]["variation_par_pas"]["travail"]
                    elif mode == "loisir":
                        besoins["detente"] += B["detente"]["satisfaction"]["loisir_par_pas"]
                    elif mode == "lecture":
                        besoins["detente"] += B["detente"]["satisfaction"]["lecture_par_pas"]
                    elif effort:
                        besoins["detente"] += B["detente"]["satisfaction"]["course_par_pas"]
                    else:
                        musique = radio or st.get("musique", False)
                        besoins["detente"] += B["detente"]["variation_par_pas"]["eveille_autre"] + (B["detente"]["satisfaction"]["musique_par_pas"] if musique else 0)
            for n, v in effets_escalier.items():
                besoins[n] += v
            for n, v in st.get("effets", {}).items():
                if n == "cafe":
                    cafe.append(i)
                elif v == "vide":
                    besoins[n] = 100
                else:
                    besoins[n] += v
            for n in besoins:
                besoins[n] = clamp(besoins[n])
            bonus = sum(8 if c <= i < c + 24 else (-4 if c + 24 <= i < c + 36 else 0) for c in cafe)

            # ---- émotions : retour vers la base, événements, besoins
            base["solitude"] = 0.25 + 0.01 * max(0.0, 75 - besoins["social"])
            for e in emo:
                hl = HL[e] / (2 if endormi else 1)
                emo[e] = base[e] + (emo[e] - base[e]) * 0.5 ** (1 / hl)
            ev_out = []
            bonus_conc = 0.0
            for ev in st.get("ev", []):
                if ev not in EV:
                    raise Incoherence(f"{hm(i)} : événement inconnu {ev}")
                spec = EV[ev]
                pensee = ev.startswith("pensee") or ev.startswith("souvenir") or ev == "anticipation_delicate"
                rum = 1.5 if pensee and i >= idx("22:30") and posture == "allongé" else 1.0
                appl = {}
                for e, d in spec["effets"].items():
                    dd = d * rum * ((0.5 + NEVRO) if negatif(e, d) else 1.0)
                    emo[e] += dd
                    appl[e] = round(dd, 3)
                bonus_conc += spec.get("concentration", 0)
                ev_out.append({"id": ev, "effets": appl} | ({"rumination": True} if rum > 1 else {}))
            if not endormi:
                if besoins["faim"] < 35:
                    emo["colere"] += 0.01
                    emo["joie"] -= 0.005
                if besoins["energie"] < 30:
                    emo["joie"] -= 0.005
                    emo["colere"] += 0.005
                if besoins["toilettes"] < 25:
                    emo["anxiete"] += 0.01
                if besoins["detente"] < 30:
                    emo["colere"] += 0.005
            for e in emo:
                emo[e] = clamp(emo[e], 1.0)
            cible = CIBLES[charge]
            if besoins["energie"] < 30:
                cible -= 0.15
            if emo["anxiete"] > 0.5 or emo["tristesse"] > 0.5:
                cible -= 0.1
            if besoins["toilettes"] < 25:
                cible -= 0.1
            conc = clamp(conc + (max(0, cible) - conc) * 0.5 + bonus_conc, 1.0)

            entry = {"pas": i, "heure": hm(i), "lieu": lieu, "piece": piece, "posture": posture,
                     "routine": s["routine"], "activite": s["titre"], "action": st["action"], "pensee": st["pensee"]}
            if dep:
                entry["deplacement"] = dep
            for opt in ("phase_sommeil", "reve", "objets", "consommation"):
                if st.get(opt):
                    entry[opt] = st[opt]
            if lum:
                entry["lumiere"] = lum
            entry["appareils_allumes"] = sorted(appareils) + [f"lumiere-{pc}" for pc, v in lumieres.items() if v]
            if ev_out:
                entry["evenements"] = ev_out
            entry["besoins"] = {n: round(v, 1) for n, v in besoins.items()} | {"energie_ressentie": round(clamp(besoins["energie"] + bonus), 1)}
            entry["emotions"] = {e: round(v, 3) for e, v in emo.items()} | {"concentration": round(conc, 3)}
            steps.append(entry)
        attendu += len(s["pas"])
    if attendu != PAS_PAR_JOUR:
        raise Incoherence(f"la journée compte {attendu} pas au lieu de {PAS_PAR_JOUR}")

    seuil = fiche["sante"]["sommeil"]["seuil_anxiete_insomnie"]
    anx = steps[idx(j.extinction)]["emotions"]["anxiete"]
    if anx > seuil:
        raise Incoherence(f"anxiété à l'extinction {anx} > {seuil} : l'endormissement devrait durer 45 minutes")

    etat_final = {"piece": piece_prec, "besoins": {n: round(v, 4) for n, v in besoins.items()},
                  "emotions": {e: round(v, 4) for e, v in emo.items()}, "concentration": round(conc, 4),
                  "lumieres": {pc: v for pc, v in lumieres.items() if v}, "appareils": sorted(appareils),
                  "positions": positions, "cafe": [c - PAS_PAR_JOUR for c in cafe if c + 36 > PAS_PAR_JOUR]}
    st_["anxiete_extinction"] = anx
    st_["seuil_insomnie"] = seuil
    return steps, etat_final, st_


# ---------------------------------------------------------------- sorties
def ecrire(fiche, j, steps, etat_initial, etat_final, st_, chemin_json, chemin_md):
    B = fiche["besoins"]
    alertes = [f"{s['heure']} {n} = {v} (seuil {B[n]['seuil_alerte']})"
               for s in steps for n, v in s["besoins"].items() if n in B and v < B[n]["seuil_alerte"]]
    conso = {}
    for s in steps:
        for c in s.get("consommation", []):
            conso.setdefault(c["produit"], []).append(str(c["quantite"]))
    nb_ev = {}
    for s in steps:
        for e in s.get("evenements", []):
            nb_ev[e["id"]] = nb_ev.get(e["id"], 0) + 1
    deplaces = {}
    for s in steps:
        for o in s.get("objets", []):
            deplaces[o["objet"]] = o["vers"]
    total = st_["entre_pieces_m"] + st_["dans_les_pieces_m"] + st_["exterieur_m"]
    deplacements = {
        "entre_pieces_m": round(st_["entre_pieces_m"]), "dans_les_pieces_m_estimes": round(st_["dans_les_pieces_m"]),
        "exterieur_m": round(st_["exterieur_m"]), "total_m": round(total), "foulees_et_marches": round(st_["foulees"]),
        "passages_de_piece": st_["passages_de_piece"], "marches_d_escalier": st_["marches"],
        "denivele_positif_m": st_["denivele_positif_m"], "denivele_negatif_m": st_["denivele_negatif_m"]}
    out = {
        "meta": {
            "personnage": fiche["meta"]["id"], "fiche_version": fiche["meta"]["version"],
            "date": j.date, "jour": j.jour, "pas_minutes": 5, "nombre_de_pas": PAS_PAR_JOUR,
            "methode": [
                f"Rédigé à la main dans outils/journees/{j.date}.py : actions, pensées, rêves, événements vécus, objets déplacés, appareils utilisés.",
                "Calculé par outils/moteur.py avec les règles de la fiche : déplacements, lumière, besoins, émotions et concentration.",
                "Aucune émotion n'est fixée à la main : chaque variation provient d'un événement listé, d'un besoin ou du retour à l'état de base.",
                "La journée part de l'état exact de la fin de la veille (etat_initial), ou de la fiche pour le premier jour.",
            ],
            "champs": {
                "besoins, emotions": "valeurs à la fin du pas",
                "deplacement": "chemin dans l'appartement (distance, durée, foulées), escalier, parcours extérieur",
                "lumiere": "interrupteurs actionnés pendant le pas",
                "appareils_allumes": "appareils et lumières allumés à la fin du pas",
                "evenements": "événements vécus et effet appliqué sur chaque émotion (après modulation par la personnalité)",
                "besoins.energie_ressentie": "énergie corrigée de l'effet du café",
            },
        },
        "resume": {
            "deplacements": deplacements,
            "lumiere": {"allumages": st_["lumiere_allumages"]},
            "evenements_vecus": nb_ev,
            **j.resume,
            "objets_deplaces_position_finale": deplaces,
            "provisions_consommees": conso,
            "besoins_sous_le_seuil_d_alerte": alertes,
            "endormissement": f"anxiété à l'extinction ({j.extinction}) : {st_['anxiete_extinction']} pour un seuil d'insomnie de {st_['seuil_insomnie']}",
            "ecarts_a_la_routine": j.ecarts,
        },
        "etat_initial": etat_initial,
        "etat_final": etat_final,
        "pas": steps,
    }
    json.dump(out, open(chemin_json, "w"), ensure_ascii=False, indent=1)

    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    an, mo, jr = map(int, j.date.split("-"))
    L = [f"# {fiche['identite']['prenom']} {fiche['identite']['nom']} — {j.jour} {jr} {mois[mo - 1]} {an}\n",
         f"Journée rédigée pas à pas (5 minutes). Les déplacements, la lumière, les besoins et les émotions sont calculés avec les règles de la fiche. Données complètes : `{j.date}.json`.\n",
         "## Déroulé\n", "| Heure | Lieu | Activité | Ce qu'il fait / pense | Événements vécus |", "|---|---|---|---|---|"]
    pos = 0
    for s in j.segments:
        n = len(s["pas"])
        bloc = steps[pos:pos + n]
        pos += n
        fin_h = hm(bloc[-1]["pas"] + 1) if bloc[-1]["pas"] < PAS_PAR_JOUR - 1 else "24:00"
        pens = [b["pensee"] for b in bloc if b.get("pensee")]
        reves = []
        for b in bloc:
            if b.get("reve") and b["reve"] not in reves:
                reves.append(b["reve"])
        if reves:
            txt = "Sommeil. Rêves : " + " / ".join(f"« {r} »" for r in reves)
        else:
            txt = bloc[0]["action"] + (" …" if n > 1 else "")
            if pens:
                txt += " — *" + " ".join(pens[:2]) + "*"
        evs, lieux = [], []
        for b in bloc:
            for e in b.get("evenements", []):
                if e["id"] not in evs:
                    evs.append(e["id"])
            if b["piece"] not in lieux:
                lieux.append(b["piece"])
        L.append(f"| {s['debut']}–{fin_h} | {', '.join(lieux)} | {s['titre']} | {txt.replace('|', '/')} | {', '.join(evs)} |")

    L += ["\n## Déplacements et lumière\n",
          f"- Entre les pièces (calculé sur le plan) : **{deplacements['entre_pieces_m']} m**, {deplacements['passages_de_piece']} passages de porte.",
          f"- Dans les pièces (estimé selon l'activité) : **{deplacements['dans_les_pieces_m_estimes']} m**.",
          f"- À l'extérieur : **{deplacements['exterieur_m']} m** (dénivelé +{deplacements['denivele_positif_m']} m / -{deplacements['denivele_negatif_m']} m).",
          f"- Escaliers : **{deplacements['marches_d_escalier']} marches**.",
          f"- Total : **{deplacements['total_m']} m**, environ **{deplacements['foulees_et_marches']} foulées et marches**.",
          f"- Lumières allumées : **{st_['lumiere_allumages']} fois**.",
          "\nTrajets notables :\n"]
    for s in steps:
        d = s.get("deplacement")
        if d and (d.get("escalier") or d.get("parcours") or len(d.get("chemin", [])) > 3):
            parts = []
            if d.get("chemin"):
                parts.append(f"{' → '.join(d['chemin'])} ({d['distance_m']} m)")
            if d.get("escalier"):
                e = d["escalier"]
                parts.append(f"escalier en {e['sens']} : {e['marches']} marches en {e['duree_s']} s")
            for x in d.get("parcours", []):
                parts.append(f"{x['moyen']} {x['distance_m']} m" + (f" ({'+' if x['denivele_m'] > 0 else ''}{x['denivele_m']} m)" if x["denivele_m"] else ""))
            L.append(f"- {s['heure']} : " + " ; ".join(parts))

    L += ["\n## Émotions au fil de la journée (calculées)\n",
          "| Heure | Joie | Tristesse | Anxiété | Colère | Solitude | Fierté | Concentration | Événements du pas |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in steps:
        if s.get("evenements") or s["heure"] in ("00:00", "12:00", "23:55"):
            if not s.get("evenements") and s["heure"] not in ("00:00", "12:00", "23:55"):
                continue
            e = s["emotions"]
            cause = ", ".join(x["id"] for x in s.get("evenements", [])) or "—"
            L.append(f"| {s['heure']} | {e['joie']:.2f} | {e['tristesse']:.2f} | {e['anxiete']:.2f} | {e['colere']:.2f} | {e['solitude']:.2f} | {e['fierte']:.2f} | {e['concentration']:.2f} | {cause} |")

    L += ["\n## Besoins au fil de la journée\n",
          "| Heure | Faim | Soif | Énergie | Énergie ressentie | Hygiène | Toilettes | Social | Détente |", "|---|---|---|---|---|---|---|---|---|"]
    for h in ["00:00", "07:00", "09:00", "12:30", "14:00", "17:00", "19:00", "22:00", "23:55"]:
        b = steps[idx(h)]["besoins"]
        L.append(f"| {h} | {b['faim']} | {b['soif']} | {b['energie']} | {b['energie_ressentie']} | {b['hygiene']} | {b['toilettes']} | {b['social']} | {b['detente']} |")

    L += ["\n## Bilan\n"] + [f"- {x}" for x in j.bilan]
    L.append(f"- **Endormissement** : {out['resume']['endormissement']}.")
    L.append("- **Écarts à la routine** :")
    L += [f"  - {e}" for e in j.ecarts]
    L.append("- **Besoins passés sous le seuil d'alerte** : " + (", ".join(alertes) if alertes else "aucun."))
    open(chemin_md, "w").write("\n".join(L) + "\n")
    return out
