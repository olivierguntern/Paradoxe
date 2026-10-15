"""Vérifie la cohérence d'une fiche de personnage.

Usage : python3 outils/verifier_fiche.py data/personnages/thomas-berthier.json

Contrôles : lieux, pièces et objets référencés, heures multiples de 5 minutes,
plan connexe (pour chaque lieu privé, toutes ses pièces atteintes depuis son
entrée), événements des déclencheurs présents dans le modèle émotionnel,
routines sans trou ni chevauchement (une étape comprise dans une autre s'y insère), capacité de travail ; pour un commerçant,
produits des paniers et des habitués présents au catalogue, horaires.
"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fiches import completer_fiche
# la fiche est vérifiée telle que le moteur la voit : complétée par le monde (data/monde/)
d = completer_fiche(json.load(open(sys.argv[1], encoding="utf-8")), os.path.splitext(os.path.basename(sys.argv[1]))[0])
lieux = {l['id'] for l in d['lieux']}
objs = {o['id'] for o in d['objets']}
pieces = {p['id'] for p in d['domicile']['pieces']}
errs = []
def m(s): h,mi = map(int, s[-5:].split(':')); return h*60+mi
def chk(s, ctx):
    if s and int(s[-2:]) % 5: errs.append(f'heure non multiple de 5: {s} ({ctx})')
for o in d['objets']:
    e = o['emplacement_initial']
    if e['lieu'] not in lieux: errs.append(f"lieu inconnu {e['lieu']} ({o['id']})")
    if e['piece'] not in pieces: errs.append(f"pièce inconnue {e['piece']} ({o['id']})")
for a in d['agenda_semaine']:
    if a['lieu'] not in lieux: errs.append(f"lieu inconnu {a['lieu']}")
    for o in a['objets_necessaires']:
        if o not in objs: errs.append(f'objet inconnu {o}')
    chk(a['debut'], a['id']); chk(a['fin'], a['id'])
travaux = d.get('travail', {}).get('travaux_en_cours_au_debut', [])
for t in travaux:
    if t['objet'] not in objs: errs.append(f"objet inconnu {t['objet']}")
for au in d['habitudes']['automatismes']:
    for o in au.get('objets', []):
        if o not in objs: errs.append(f'objet inconnu {o}')
pl = d['domicile']['plan']['liaisons']
exterieurs = set(d['domicile']['plan'].get('noeuds_exterieurs', []))
noeuds = pieces | {'palier'} | exterieurs
for l in pl:
    for k in ('a','b'):
        if l[k] not in noeuds: errs.append(f"pièce inconnue dans le plan : {l[k]}")
def atteintes(depart):
    """Pièces atteintes depuis une pièce, sans passer par l'extérieur."""
    reach, changed = {depart}, True
    while changed:
        changed = False
        for l in pl:
            for x, y in ((l['a'], l['b']), (l['b'], l['a'])):
                if x in reach and y not in reach and y in pieces: reach.add(y); changed = True
    return reach
entrees = d['domicile']['plan'].get('entrees') or {None: d['domicile']['pieces'][0]['id']}
lieu_de = {pc['id']: pc.get('lieu') for pc in d['domicile']['pieces']}
for lieu, entree in entrees.items():
    reach = atteintes(entree)
    for pc in pieces:
        if (lieu is None or lieu_de[pc] == lieu) and pc not in reach:
            errs.append(f"pièce non reliée à l'entrée ({entree}) : {pc}")
        if lieu is not None and pc in reach and lieu_de[pc] != lieu:
            errs.append(f"pièce {pc} ({lieu_de[pc]}) reliée à l'intérieur de « {lieu} »")
if 'entrees' in d['domicile']['plan']:
    for pc in pieces:
        if lieu_de[pc] not in entrees: errs.append(f"pièce sans lieu connu : {pc}")
for ev in [x['evenement'] for x in d['vie_interieure']['declencheurs']]:
    if ev not in d['modele_emotionnel']['evenements']: errs.append(f"événement inconnu : {ev}")
if 'perception' in d:
    pc = d['perception']
    for cle, ev in pc['evenements'].items():
        if ev not in d['modele_emotionnel']['evenements']: errs.append(f"perception : événement inconnu {ev} ({cle})")
    for app, spec in pc['ouie'].items():
        if spec.get('piece') and spec['piece'] not in pieces: errs.append(f"perception : pièce inconnue {spec['piece']} ({app})")
        if spec['portee'] not in ('piece', 'voisines', 'logement'): errs.append(f"perception : portée inconnue {spec['portee']} ({app})")
    for lieu in pc.get('personnes', {}):
        if lieu not in lieux: errs.append(f"perception : lieu inconnu {lieu}")
    for p in pieces - set(pc['pieces']): errs.append(f"perception : pièce sans nom {p}")
valid_lieux = pieces | lieux | exterieurs | {'trajet'}
jours = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
for j in jours:
    steps = []
    for r in d['habitudes']['routines']:
        if j in r['jours']:
            for e in r['etapes']:
                chk(e['debut'], r['id']); chk(e['fin'], r['id'])
                if e['lieu'] not in valid_lieux: errs.append(f"lieu d'étape inconnu {e['lieu']} ({r['id']})")
                fin = m(e['fin']) if e['fin'] else 24*60
                steps.append((m(e['debut']), fin, r['id'], e['action'][:40]))
    steps.sort(key=lambda x: (x[0], -x[1]))
    # une étape entièrement comprise dans une autre s'y insère (des courses prises sur le temps libre) : l'habitant
    # générique fait la plus courte ; le reste de la journée doit s'enchaîner sans trou ni chevauchement
    inserees = [s for s in steps if any(o is not s and o[0] <= s[0] and s[1] <= o[1] and (o[1] - o[0]) > (s[1] - s[0]) for o in steps)]
    steps = [s for s in steps if s not in inserees]
    for a, b in zip(steps, steps[1:]):
        if b[0] < a[1]: errs.append(f"{j}: chevauchement {a[2]} {a[0]//60:02}:{a[0]%60:02}-{a[1]//60:02}:{a[1]%60:02} / {b[2]} {b[0]//60:02}:{b[0]%60:02}")
        elif b[0] > a[1]: errs.append(f"{j}: trou {a[1]//60:02}:{a[1]%60:02}-{b[0]//60:02}:{b[0]%60:02}")
    print(j, f"{steps[0][0]//60:02}:{steps[0][0]%60:02} → coucher", f"{len(steps)} étapes" + (f", {len(inserees)} insérée(s)" if inserees else ""))
C = d.get('commerce')
if C:
    cat = {x['produit'] for x in C['catalogue']}
    for moment, poids in C['paniers'].items():
        if moment == 'principe': continue
        for pid in poids:
            if pid not in cat: errs.append(f"produit de panier absent du catalogue : {pid} ({moment})")
    for pid in C.get('par_plusieurs', {}):
        if pid not in cat: errs.append(f"produit absent du catalogue : {pid} (par_plusieurs)")
    for h in C['clients_habitues']:
        chk(h['heure'], h['nom'])
        for pid, _ in h['panier']:
            if pid not in cat: errs.append(f"produit absent du catalogue : {pid} ({h['nom']})")
    for j_, plages_ in C['horaires'].items():
        for a_, b_ in plages_:
            chk(a_, f'horaires {j_}'); chk(b_, f'horaires {j_}')
            if m(b_) <= m(a_): errs.append(f'horaires {j_} : {a_}-{b_}')
    for x in C['catalogue']:
        if x['stock_initial'] < 0 or x['cible'] < 0: errs.append(f"stock négatif : {x['produit']}")
    print('catalogue :', len(cat), 'produits ;', 'ouvert', sum(1 for v in C['horaires'].values() if v), 'jours sur 7')
if travaux:
    cap = 0
    for j in jours[:5]:
        cap += 415 - (60 if j == 'vendredi' else 0)
    need = sum(t['temps_restant_minutes'] for t in travaux)
    print('capacité atelier (min):', cap, '| travaux:', need)
print('\n'.join(errs) or 'OK')
sys.exit(1 if errs else 0)
