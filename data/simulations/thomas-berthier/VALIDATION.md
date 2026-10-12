# Validation de l'agent autonome

L'agent autonome (`outils/agent.py`) a vécu seul la semaine de Thomas du lundi 8 au mercredi 10 mars 2010, à partir de la fiche. Ses journées, dans ce dossier, sont comparées pas à pas aux journées de référence rédigées à la main (`data/timelines/thomas-berthier/`).

```bash
python3 outils/simuler_agent.py 2010-03-08 2010-03-10 --dossier data/simulations/thomas-berthier
python3 outils/comparer_journees.py data/timelines/thomas-berthier/2010-03-09.json data/simulations/thomas-berthier/2010-03-09.json
```

## Concordance des faits (288 pas par jour)

| Critère | Lundi | Mardi | Mercredi |
|---|---|---|---|
| Pièce | 100 % | 100 % | 100 % |
| Lieu (domicile, extérieur) | 100 % | 100 % | 100 % |
| Posture | 100 % | 100 % | 99,3 % |
| Appareils et lumières allumés | 100 % | 100 % | 100 % |
| Position de chaque objet | 99,7 % | 100 % | 100 % |
| Stock de chaque provision | 100 % | 100 % | 100 % |
| État de fin de journée (objets, stock, pièce) | identique | identique | identique |

## Écarts restants

| Jour | Heure | Écart | Cause |
|---|---|---|---|
| Lundi | 17:50 | La clé du coffre est rangée 5 minutes plus tôt | L'agent range toujours la clé avec les montres ; la référence l'avait rangée au pas suivant |
| Mercredi | 19:35-19:40 | Debout au lieu d'assis | La fermeture de séance de l'agent se fait debout ; la référence restait assise |

## Ce qui diffère volontairement

- **Les pensées** : l'agent les choisit dans des modèles (`data/agents/thomas-berthier/pensees.json`). Les textes et les événements de pensée (penser à son père, à Sophie…) ne tombent donc pas aux mêmes instants.
- **Les émotions**, qui en découlent : écart moyen de 0,00 à 0,03 sur une échelle de 0 à 1.
- **Les besoins** : identiques, sauf la soif (écart moyen inférieur à 0,1 sur 100), car le verre d'eau de la pause café n'est pas compté au même pas.

## Décisions reproduites par des règles, et non recopiées

| Décision | Règle de l'agent |
|---|---|
| Poulet mis au four à 11:50 (lundi) | Un plat long à cuire est mis en route avant midi |
| Soupe commencée à 18:20 (lundi), dîner à 19:00 (mardi) | Le dîner, vaisselle comprise, se termine à 20:00 |
| Livre oublié au séjour, puis rangé dès mardi | Un oubli crée une habitude |
| Montres à quartz pendant le cycle de la machine (mardi) | Un groupe court est intercalé pendant une attente |
| Validation de l'Omega à 17:00 mardi | Une observation de 24 h terminée passe avant tout |
| Montres à quartz plutôt que la pendule à 17:15 (mardi) | Seulement des tâches légères dans la dernière heure |
| Séance arrêtée à 21:25 et coucher à 22:15 (mardi) | Fatigue : énergie sous le seuil |
| Réveil à 06:55 avant la sonnerie (mercredi) | Réveil naturel après plus de 8 h 25 de sommeil |
| Endormissement en 45 minutes (mercredi) | Excitation du match au-dessus du seuil |

## Règles ajoutées après la validation

Ces règles ne changent rien à la reproduction de lundi à mercredi (mêmes taux de concordance) ; elles servent aux journées que l'agent vit seul, de jeudi à dimanche.

| Règle | Effet |
|---|---|
| Interruption par un besoin | Si les toilettes (seuil 25), la soif (seuil 40) ou la faim (seuil 35) passent sous leur seuil d'alerte pendant l'atelier, une séance, la lecture, la musique, le temps libre ou la grasse matinée, l'agent s'interrompt un pas pour y répondre, puis reprend. Pas d'interruption si l'activité se termine dans les 10 minutes, ni pour la faim dans les 45 minutes qui précèdent un repas. |
| Hydratation avant la course | Un verre d'eau avant de partir ; un second si la soif prévue au départ est sous 45 |
| Tenue de course | Prise là où elle se trouve réellement (armoire, étendoir, panier à linge) |
| Montre à sortir du coffre | Une montre rangée au coffre est sortie avant sa première opération du jour |
| Réveil du week-end | Sans sonnerie : pas avant 07:30, au plus tard 08:30 |
| Anticipation avant une séance | Avant une séance sur la montre du grand-père, il passe aux toilettes ou boit un verre d'eau si le besoin passerait sous son seuil d'alerte avant la fin prévue |
| Livre terminé | Quand la dernière page est atteinte, l'événement `livre_termine` est vécu. Le livre est rangé et le reste de la plage de lecture devient de la musique |
| Livre suivant | À la séance de lecture suivante au séjour, il range le livre fini dans la bibliothèque et prend le suivant (`regles.json`, `lecture.livres`) ; sans livre suivant, la plage devient de la musique |
