# Paradoxe — document de conception

## Le concept

Une **mini-ville de 2010** dont chaque habitant vit sa vie de façon déterministe, à quelques minutes près : routines, besoins, émotions, objets, déplacements. Cette vie constitue **l'histoire de référence**.

Le joueur incarne un **voyageur venu du futur**. Il arrive dans cette époque avec des missions (définies plus tard) et doit les accomplir **sans provoquer de paradoxe**.

Le terrain de jeu, c'est la connaissance fine de la vie des habitants : savoir qui sort à quelle heure, qui remarque quoi, quel objet compte pour qui.

## Le voyageur

- Il cherche à être **compatible avec l'époque** : vêtements, argent, comportement, objets de 2010.
- Il peut être vu : pour un habitant, il n'est qu'un **passant**, sans conséquence.
- Un anachronisme visible (objet ou comportement qui n'existe pas en 2010) est en revanche une anomalie qu'un habitant peut remarquer.
- Ses missions seront définies plus tard.

## Le paradoxe

### Ce qui n'est pas un paradoxe
- Être vu par un habitant.
- Une interaction minime : entrer dans un bar, boire un café, croiser quelqu'un dans la rue.

Ces écarts sont **absorbés** : le temps est **résilient**. C'est une règle du jeu ; en physique, l'idée d'un temps qui « se referme » reste une hypothèse (principe d'auto-cohérence de Novikov), pas un résultat démontré.

### Ce qui crée un paradoxe
Une intervention du voyageur sur une **action** d'un habitant, qui modifie **en cascade** un nombre croissant de choses : décisions, rencontres, objets, horaires, puis la vie d'autres habitants.

### Mesure envisagée
Deux mondes sont simulés en parallèle :
- le **monde de référence**, sans le voyageur ;
- le **monde joué**, avec ses interventions.

Le jeu compare les deux à chaque pas, en distinguant deux niveaux :

| Niveau | Exemples | Traitement |
|---|---|---|
| **Détails** | Émotions légèrement différentes, quelques secondes d'écart, une tasse de café en moins dans le stock d'un bar | Tolérés et absorbés avec le temps |
| **Faits** | Une action faite ou non, une décision, un objet qui change de main, une rencontre, un retard qui en entraîne d'autres | Comptés dans la divergence |

La **divergence** suit le nombre de faits différents et le nombre d'habitants touchés au fil du temps :
- si elle reste faible et se résorbe, le temps l'a absorbée ;
- si elle **s'amplifie** (effet de cascade), le paradoxe approche ; au-delà d'un seuil, il survient.

Certains **événements-clés** (importants pour le futur) pourront compter plus que les autres.

## Conséquences techniques

1. **Habitants autonomes** : chaque habitant décide lui-même de ses actions (routines, besoins, perceptions). Sans voyageur, la simulation doit reproduire exactement l'histoire de référence.
2. **Perception** : ce que chaque habitant voit, entend et remarque. Ce qu'il croit est séparé de ce qui est réel.
3. **Chaînes de causes** : chaque fait garde la trace de ce qui l'a provoqué, pour suivre une cascade jusqu'à son origine.
4. **Temps variable** : un pas de 5 minutes par défaut, un pas plus fin quand le voyageur est proche d'un habitant.
5. **Niveau de détail variable** : simulation complète pour les habitants proches du voyageur ou touchés par une cascade, simulation simplifiée pour les autres, afin de faire vivre une ville entière.

## Feuille de route

| Étape | Contenu | État |
|---|---|---|
| 1 | Un habitant (Thomas Berthier), semaine de référence rédigée et vérifiée par le moteur | Fait : lundi à mercredi rédigés, jeudi à dimanche vécus par l'agent |
| 2 | Thomas autonome : le moteur décide de ses actions et reproduit la semaine de référence | Fait : lundi à mercredi reproduits (voir `data/simulations/thomas-berthier/VALIDATION.md`) ; jeudi à dimanche générés seuls, avec interruptions par les besoins |
| 3 | Perception : ce que Thomas voit, entend, remarque | À faire |
| 4 | Le voyageur dans le monde de Thomas ; mesure de la divergence entre les deux mondes | À faire |
| 5 | Plusieurs habitants et lieux partagés (rue, bar, commerces) | À faire |
| 6 | La mini-ville : génération des habitants, niveaux de détail | À faire |
| 7 | Missions du voyageur | Plus tard |
| 8 | Interface de jeu | Commencée : vue isométrique fil de fer de la semaine (`vue/`), plan à valider |
