# Validation de l'agent de Robert Chazal

L'agent du commerçant (`outils/agent_epicier.py`) a vécu seul les journées du lundi 8 au mercredi 10 mars 2010, à partir de la fiche de Robert. Ses journées, dans ce dossier, sont comparées pas à pas aux journées de référence rédigées à la main (`data/references/robert-chazal/`, écrites dans `outils/journees/robert-chazal/`).

```bash
python3 outils/simuler_agent.py 2010-03-08 2010-03-10 --personnage robert-chazal --dossier data/simulations/robert-chazal
python3 outils/comparer_journees.py data/references/robert-chazal/2010-03-09.json data/simulations/robert-chazal/2010-03-09.json
```

Les clients anonymes viennent du même flux déterministe (`outils/clientele.py`) dans la référence et chez l'agent : ce sont les mêmes personnes, aux mêmes minutes. Ce qui leur est vendu dépend en revanche du stock du magasin au moment du passage, donc des livraisons, des prélèvements et des ventes précédentes de chaque journée.

## Concordance des faits (288 pas par jour)

| Critère | Lundi | Mardi | Mercredi |
|---|---|---|---|
| Pièce | 100 % | 100 % | 100 % |
| Lieu (maison, boutique, voiture, extérieur) | 100 % | 100 % | 100 % |
| Posture | 100 % | 100 % | 100 % |
| Appareils et lumières allumés | 100 % | 100 % | 100 % |
| Position de chaque objet | 100 % | 100 % | 100 % |
| Stock de chaque provision de la maison | 100 % | 100 % | 100 % |
| Stock de chaque produit du magasin | 100 % | 100 % | 100 % |
| Argent (espèces, compte, caisse, coffre, ardoises) | 100 % | 100 % | 100 % |
| État de fin de journée (objets, stock, pièce) | identique | identique | identique |

## Ce qui diffère

- **Les pensées et les textes** : l'agent les tire de ses modèles (`data/agents/robert-chazal/pensees.json`) et de ses scènes ; les notes écrites à la main dans la référence (une pensée à 08:45, un client qui demande un pronostic…) ne tombent pas aux mêmes pas.
- **Les besoins** : identiques, sauf les toilettes au comptoir (écart moyen 2,5 à 2,9 sur 100) et la soif le mercredi (0,4) : la référence place le passage aux toilettes de l'après-midi à 17:15 ou 17:20, l'agent y va au premier pas où le besoin passe sous 45. Ce passage est un aller-retour au fond de la boutique : la pièce, à la fin du pas, reste la boutique.
- **Les émotions**, qui en découlent : écart moyen de 0,001 à 0,012 sur une échelle de 0 à 1.

## Décisions reproduites par des règles

| Décision | Règle de l'agent |
|---|---|
| Bon de commande du lundi (31 lignes), livré mardi à 06:40 | Chaque produit sec ou frais de rayon ramené à son stock cible ; la livraison reprend le bon |
| Deux packs de yaourts et une laitue jetés au ménage du lundi | Part des produits à date courte jetés (12 % des yaourts, 20 % des laitues) |
| Pommes de terre, carottes et laitue rapportées lundi ; œufs, oignon et tomates mardi ; jambon, emmental et riz mercredi | Il prélève au magasin ce qui manque à la maison pour les repas de Josiane jusqu'au premier repas qui suit son prochain départ de la boutique |
| Une baguette mise de côté chaque matin à la livraison du pain | Habitude ; deux le dimanche |
| Caisse vidée dans la sacoche du coffre à midi et le soir | Tout ce qui dépasse le fond de caisse de 150 € |
| Dépôt de la recette de la semaine au coffre de la banque, lundi | Le coffre de l'arrière-boutique est vidé sur le compte |
| Ardoise des étudiantes, mercredi | Paiement « sur l'ardoise » des habituées qui le demandent ; noté au carnet |
| Coucher à 22:00 mardi au lieu de 22:30 | Fatigue : énergie sous 25 devant la télévision, après une nuit de six heures (cinéma la veille) |
| Endormissement en 45 minutes mercredi | Excitation de la qualification au-dessus du seuil |

## Jeudi à dimanche, vécus par l'agent seul

| Jour | Ce que l'agent a décidé |
|---|---|
| Jeudi | Après une nuit de 5 h 45, il oublie le cabas au portemanteau ; il le voit à midi et le reprend. Bon de commande du soir pour vendredi. Couché à 21:20, épuisé. |
| Vendredi | Livraison du grossiste ; les étudiantes règlent leur ardoise de mercredi (5,80 €). Haricots verts, pommes et beurre rapportés pour le week-end. |
| Samedi | L'horloger passe à 11:50 ; Robert lui conseille « The Ghost Writer », vu lundi avec Josiane (l'horloger ira le soir même). Deux pommes, un morceau de comté et un pain de campagne, 7,40 €. Pizza de Josiane, puis belote avec les Morel jusqu'à 23:00. |
| Dimanche | Nouveau cabas oublié après la belote : les courses rentrent dans un carton de la réserve. Vote au premier tour des régionales, randonnée dans les monts d'Or, couché à 20:40. |
