# Paradoxe

Prototype d'un jeu de réflexion sur les paradoxes temporels, jouable dans le navigateur.

## Principe

Vous pouvez remonter le temps à tout moment. La boucle que vous venez de jouer devient alors un **écho** : une version passée de vous qui rejoue exactement le même trajet pendant que vous agissez dans le présent.

Les échos tiennent des plaques, ouvrent des portes, et permettent d'accomplir à plusieurs ce qui est impossible seul. Mais le passé est figé : si le présent empêche un écho de refaire ce qu'il a fait, la chronologie s'effondre. C'est un **paradoxe**.

Un paradoxe se produit lorsque :

- un écho doit franchir une porte qui est désormais fermée ;
- un écho et vous occupez la même case, ou vous vous croisez de face.

## Jouer

Ouvrir `index.html` dans un navigateur (aucune installation requise), ou lancer un serveur local :

```bash
npm start   # http://localhost:8080
```

### Commandes

| Action | Clavier | Tactile |
|---|---|---|
| Se déplacer | Flèches, ZQSD ou WASD | Croix directionnelle ou glisser sur le plateau |
| Attendre un tour | Espace | ⏸ |
| Remonter le temps | R | « Remonter le temps » |
| Annuler | Retour arrière ou U | « Annuler » |
| Recommencer le niveau | N | « Recommencer » |

### Éléments

| Symbole (carte) | Élément |
|---|---|
| `@` | Machine temporelle (départ, point de retour des boucles) |
| `>` | Sortie |
| `1`–`9` | Plaque de pression |
| `a`–`i` | Porte ouverte quand la plaque correspondante est pressée (`a`↔`1`, `b`↔`2`…) |
| `A`–`I` | Porte inversée : fermée quand la plaque correspondante est pressée |
| `#` | Mur |

## Structure

```
index.html          page du jeu
style.css           apparence
src/engine.js       moteur (logique pure, testable sous Node)
src/levels.js       définition des niveaux
src/game.js         rendu canvas et commandes
tests/              tests du moteur, dont la résolution de chaque niveau
```

## Ajouter un niveau

Ajouter une entrée dans `src/levels.js` (carte ASCII, `maxEchoes`, `timeLimit`), puis une séquence de solution dans `tests/engine.test.js` pour garantir qu'il reste résoluble :

```bash
npm test
```
