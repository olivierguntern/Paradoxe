const test = require('node:test');
const assert = require('node:assert/strict');
const E = require('../src/engine.js');
const LEVELS = require('../src/levels.js');

const KEYS = { U: 'up', D: 'down', L: 'left', R: 'right', W: 'wait' };

// Joue une séquence : U/D/L/R/W pour bouger ou attendre, T pour remonter le temps.
function play(game, seq) {
  let last = null;
  for (const c of seq.replace(/\s+/g, '')) {
    if (c === 'T') {
      const r = E.rewind(game);
      assert.ok(r.ok, r.reason);
      last = r;
    } else {
      last = E.step(game, KEYS[c]);
      assert.notEqual(last.type, 'blocked', `déplacement bloqué (${c}) à t=${E.now(game)}`);
      if (last.type === 'paradox' || last.type === 'won') return last;
    }
  }
  return last;
}

const SOLUTIONS = [
  'RRR WWWW T  DRRR DD',
  'RRRR WWWWWWWWWWWW T  DRRRR DDL WWWWWWWW T  W DRRRR DD RR DD D R',
  'D RRRR DDD LL WWWWWWWWWW T  WWWWWW RRR WWWWWWWWWWW T  W D RRRR DD RR DD D LL DD',
];

test('chaque niveau se charge', () => {
  for (const def of LEVELS) {
    const game = E.createGame(def);
    assert.equal(game.status, 'playing');
  }
});

LEVELS.forEach((def, i) => {
  test(`niveau ${i + 1} (${def.name}) est résoluble`, () => {
    const game = E.createGame(def);
    const result = play(game, SOLUTIONS[i]);
    assert.equal(result.type, 'won', game.message || '');
  });
});

test('une porte fermée bloque le joueur', () => {
  const game = E.createGame(LEVELS[0]);
  play(game, 'DRRR');
  assert.deepEqual(E.step(game, 'down'), { type: 'blocked', reason: 'door' });
});

test("un écho qui entre dans la case du joueur provoque un paradoxe", () => {
  const game = E.createGame(LEVELS[0]);
  play(game, 'WRRR T R');
  const r = E.step(game, 'wait');
  assert.equal(r.type, 'paradox');
  assert.match(r.message, /même case/);
});

test("presser la plaque trop tôt ferme la porte inversée devant l'écho", () => {
  const game = E.createGame(LEVELS[2]);
  const r = play(game, 'D RRRR DDD LL WWWWWWWWWW T  RRR WWW');
  assert.equal(r.type, 'paradox');
  assert.match(r.message, /porte fermée/);
});

test("annuler restaure l'état d'avant le paradoxe", () => {
  const game = E.createGame(LEVELS[0]);
  play(game, 'WRRR T R');
  E.step(game, 'wait');
  assert.equal(game.status, 'paradox');
  assert.ok(E.undo(game));
  assert.equal(game.status, 'playing');
  assert.equal(E.now(game), 1);
});

test('annuler au début d\'une boucle annule le retour dans le temps', () => {
  const game = E.createGame(LEVELS[0]);
  play(game, 'RR T');
  assert.equal(game.echoes.length, 1);
  E.undo(game);
  assert.equal(game.echoes.length, 0);
  assert.equal(E.now(game), 2);
});

test('le nombre d\'échos est limité', () => {
  const game = E.createGame(LEVELS[0]);
  play(game, 'D T R');
  const r = E.rewind(game);
  assert.equal(r.ok, false);
  assert.match(r.reason, /Limite/);
});

test('la fin du temps renvoie automatiquement au départ', () => {
  const game = E.createGame(LEVELS[1]);
  let r;
  for (let i = 0; i < LEVELS[1].timeLimit; i++) r = E.step(game, 'wait');
  assert.equal(r.type, 'timeout');
  assert.equal(game.echoes.length, 1);
  assert.equal(E.now(game), 0);
});
