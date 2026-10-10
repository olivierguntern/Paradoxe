/*
 * Niveaux de Paradoxe. Légende : voir parseLevel() dans engine.js.
 */
(function (root) {
  'use strict';

  const LEVELS = [
    {
      name: 'Premier saut',
      intro:
        "La porte ne s'ouvre que si quelqu'un se tient sur la plaque. Vous êtes seul… pour l'instant. " +
        'Allez sur la plaque, attendez, puis remontez le temps (R) : votre passé la tiendra pour vous.',
      maxEchoes: 1,
      timeLimit: 20,
      map: [
        '#########',
        '#@..1...#',
        '#.......#',
        '####a####',
        '#...>...#',
        '#########',
      ],
    },
    {
      name: 'Relais',
      intro:
        'Deux portes, deux plaques. Chaque écho rejoue exactement votre trajet : ' +
        'suivez-les sans jamais occuper leur case.',
      maxEchoes: 2,
      timeLimit: 24,
      map: [
        '###########',
        '#@...1....#',
        '#.........#',
        '#####a#####',
        '#...2.....#',
        '#.........#',
        '#######b###',
        '#.......>.#',
        '###########',
      ],
    },
    {
      name: 'Le grand-père',
      intro:
        "La porte rayée est inversée : elle se ferme quand sa plaque est pressée. " +
        "Si vous la fermez avant qu'un écho ne la franchisse, son passé devient impossible.",
      maxEchoes: 2,
      timeLimit: 30,
      map: [
        '#############',
        '#@..1.......#',
        '#...........#',
        '#####A#######',
        '#...........#',
        '#..2........#',
        '#######b#####',
        '#...........#',
        '#####a#######',
        '#....>......#',
        '#############',
      ],
    },
  ];

  if (typeof module !== 'undefined' && module.exports) module.exports = LEVELS;
  else root.PARADOXE_LEVELS = LEVELS;
})(typeof globalThis !== 'undefined' ? globalThis : this);
