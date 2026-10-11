"""Vérifie la cohérence d'une fiche de personnage.

Usage : python3 outils/verifier_fiche.py data/personnages/thomas-berthier.json

Contrôles : lieux, pièces et objets référencés, heures multiples de 5 minutes,
plan de l'appartement connexe, événements des déclencheurs présents dans le
modèle émotionnel, routines sans trou ni chevauchement, capacité de travail.
"""
import json, re, sys
d = json.load(open(sys.argv[1]))
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
for t in d['travail']['travaux_en_cours_au_debut']:
    if t['objet'] not in objs: errs.append(f"objet inconnu {t['objet']}")
for au in d['habitudes']['automatismes']:
    for o in au.get('objets', []):
        if o not in objs: errs.append(f'objet inconnu {o}')
pl = d['domicile']['plan']['liaisons']
for l in pl:
    for k in ('a','b'):
        if l[k] not in pieces | {'palier'}: errs.append(f"pièce inconnue dans le plan : {l[k]}")
reach = {'entree'}
changed = True
while changed:
    changed = False
    for l in pl:
        for x, y in ((l['a'], l['b']), (l['b'], l['a'])):
            if x in reach and y not in reach: reach.add(y); changed = True
for pc in pieces:
    if pc not in reach: errs.append(f"pièce non reliée au plan : {pc}")
for ev in [x['evenement'] for x in d['vie_interieure']['declencheurs']]:
    if ev not in d['modele_emotionnel']['evenements']: errs.append(f"événement inconnu : {ev}")
valid_lieux = pieces | lieux | {'trajet'}
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
    steps.sort()
    for a, b in zip(steps, steps[1:]):
        if b[0] < a[1]: errs.append(f"{j}: chevauchement {a[2]} {a[0]//60:02}:{a[0]%60:02}-{a[1]//60:02}:{a[1]%60:02} / {b[2]} {b[0]//60:02}:{b[0]%60:02}")
        elif b[0] > a[1]: errs.append(f"{j}: trou {a[1]//60:02}:{a[1]%60:02}-{b[0]//60:02}:{b[0]%60:02}")
    print(j, f"{steps[0][0]//60:02}:{steps[0][0]%60:02} → coucher", f"{len(steps)} étapes")
cap = 0
for j in jours[:5]:
    cap += 415 - (60 if j == 'vendredi' else 0)
need = sum(t['temps_restant_minutes'] for t in d['travail']['travaux_en_cours_au_debut'])
print('capacité atelier (min):', cap, '| travaux:', need)
print('\n'.join(errs) or 'OK')
sys.exit(1 if errs else 0)
