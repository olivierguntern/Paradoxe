/*
 * Paradoxe — moteur de jeu (logique pure, sans rendu).
 *
 * Principe : chaque boucle temporelle enregistre la trajectoire du joueur.
 * Lors d'un retour dans le temps, cette trajectoire devient un « écho » qui
 * rejoue exactement les mêmes positions. Si le présent empêche un écho de
 * refaire ce qu'il a fait (porte fermée, collision), la chronologie devient
 * incohérente : c'est un paradoxe.
 *
 * Utilisable dans le navigateur (window.ParadoxeEngine) et dans Node (require).
 */
(function (root) {
  'use strict';

  const DIRS = {
    up: [0, -1],
    down: [0, 1],
    left: [-1, 0],
    right: [1, 0],
    wait: [0, 0],
  };

  function samePos(a, b) {
    return Boolean(a && b && a.x === b.x && a.y === b.y);
  }

  /*
   * Légende des cartes :
   *   #  mur              .  sol
   *   @  machine temporelle (départ)
   *   >  sortie
   *   1-9  plaque de pression
   *   a-i  porte ouverte quand la plaque correspondante (a=1, b=2…) est pressée
   *   A-I  porte inversée : ouverte quand la plaque correspondante est LIBRE
   */
  function parseLevel(def) {
    const rows = def.map;
    const height = rows.length;
    const width = Math.max(...rows.map((r) => r.length));
    const walls = new Set();
    const plates = [];
    const doors = [];
    let start = null;
    let exit = null;

    rows.forEach((row, y) => {
      for (let x = 0; x < width; x++) {
        const c = row[x] || '#';
        if (c === '#') walls.add(x + ',' + y);
        else if (c === '@') start = { x, y };
        else if (c === '>') exit = { x, y };
        else if (/[1-9]/.test(c)) plates.push({ x, y, id: c });
        else if (/[a-i]/.test(c)) doors.push({ x, y, id: String(c.charCodeAt(0) - 96), inverse: false });
        else if (/[A-I]/.test(c)) doors.push({ x, y, id: String(c.charCodeAt(0) - 64), inverse: true });
        else if (c !== '.') throw new Error(`Caractère inconnu « ${c} » en (${x}, ${y}) dans « ${def.name} »`);
      }
    });

    if (!start) throw new Error(`Niveau « ${def.name} » : départ (@) manquant`);
    if (!exit) throw new Error(`Niveau « ${def.name} » : sortie (>) manquante`);

    return {
      name: def.name,
      intro: def.intro || '',
      width,
      height,
      walls,
      plates,
      doors,
      start,
      exit,
      maxEchoes: def.maxEchoes,
      timeLimit: def.timeLimit,
    };
  }

  function createGame(def) {
    const level = parseLevel(def);
    return {
      level,
      echoes: [], // chaque écho = tableau de positions indexé par le temps
      path: [{ ...level.start }], // trajectoire de la boucle en cours
      status: 'playing', // 'playing' | 'won' | 'paradox'
      message: null,
    };
  }

  function now(game) {
    return game.path.length - 1;
  }

  function echoPos(echo, t) {
    return t < echo.length ? echo[t] : null;
  }

  function isWall(level, p) {
    return p.x < 0 || p.y < 0 || p.x >= level.width || p.y >= level.height || level.walls.has(p.x + ',' + p.y);
  }

  function entitiesAt(game, t) {
    const list = [];
    game.echoes.forEach((echo, index) => {
      const pos = echoPos(echo, t);
      if (pos) list.push({ kind: 'echo', index, pos });
    });
    if (game.path[t]) list.push({ kind: 'player', pos: game.path[t] });
    return list;
  }

  function pressedPlates(game, t) {
    const ents = entitiesAt(game, t);
    const pressed = new Set();
    for (const plate of game.level.plates) {
      if (ents.some((e) => samePos(e.pos, plate))) pressed.add(plate.id);
    }
    return pressed;
  }

  // Une porte occupée reste ouverte : elle ne peut pas se refermer sur quelqu'un.
  function doorStates(game, t) {
    const pressed = pressedPlates(game, t);
    const ents = entitiesAt(game, t);
    return game.level.doors.map((door) => {
      const active = pressed.has(door.id);
      const occupied = ents.some((e) => samePos(e.pos, door));
      return { ...door, open: occupied || (door.inverse ? !active : active) };
    });
  }

  function findParadox(game, t, doors) {
    const start = game.level.start;
    const p0 = game.path[t];
    const p1 = game.path[t + 1];

    for (let i = 0; i < game.echoes.length; i++) {
      const a = echoPos(game.echoes[i], t);
      const b = echoPos(game.echoes[i], t + 1);
      if (!a || !b) continue;
      const n = i + 1;

      if (!samePos(a, b)) {
        const door = doors.find((d) => samePos(d, b));
        if (door && !door.open) {
          return `L'écho n°${n} se heurte à une porte fermée : le passé que vous avez vécu ne peut plus avoir eu lieu.`;
        }
      }
      if (samePos(b, p1) && !samePos(b, start)) {
        return `L'écho n°${n} occupe la même case que vous : deux versions de vous se rencontrent.`;
      }
      if (samePos(a, p1) && samePos(b, p0) && !samePos(a, b)) {
        return `Vous croisez l'écho n°${n} de face : deux versions de vous se rencontrent.`;
      }
    }
    return null;
  }

  function step(game, action) {
    if (game.status !== 'playing') return { type: 'ignored' };
    const d = DIRS[action];
    if (!d) throw new Error(`Action inconnue : ${action}`);

    const t = now(game);
    const from = game.path[t];
    const to = { x: from.x + d[0], y: from.y + d[1] };
    const doors = doorStates(game, t);

    if (action !== 'wait') {
      if (isWall(game.level, to)) return { type: 'blocked', reason: 'wall' };
      const door = doors.find((dd) => samePos(dd, to));
      if (door && !door.open) return { type: 'blocked', reason: 'door' };
      if (!samePos(to, game.level.start) && game.echoes.some((e) => samePos(echoPos(e, t + 1), to))) {
        return { type: 'blocked', reason: 'echo' };
      }
    }

    game.path.push(to);

    const paradox = findParadox(game, t, doors);
    if (paradox) {
      game.status = 'paradox';
      game.message = paradox;
      return { type: 'paradox', message: paradox };
    }

    if (samePos(to, game.level.exit)) {
      game.status = 'won';
      return { type: 'won' };
    }

    if (t + 1 >= game.level.timeLimit) {
      const r = rewind(game);
      if (!r.ok) {
        game.status = 'paradox';
        game.message = 'Le temps de la boucle est écoulé et aucun retour supplémentaire n\'est possible.';
        return { type: 'paradox', message: game.message };
      }
      return { type: 'timeout', echoes: r.echoes };
    }

    return { type: 'moved' };
  }

  function rewind(game) {
    if (game.status !== 'playing') return { ok: false, reason: 'La chronologie est figée.' };
    if (now(game) === 0) return { ok: false, reason: 'Rien à enregistrer : effectuez au moins une action.' };
    if (game.echoes.length >= game.level.maxEchoes) {
      return { ok: false, reason: `Limite atteinte : ${game.level.maxEchoes} écho(s) maximum dans ce niveau.` };
    }
    game.echoes.push(game.path.slice());
    game.path = [{ ...game.level.start }];
    return { ok: true, echoes: game.echoes.length };
  }

  // Annule la dernière action ; au début d'une boucle, annule le retour dans le temps.
  function undo(game) {
    if (game.path.length > 1) {
      game.path.pop();
    } else if (game.echoes.length > 0) {
      game.path = game.echoes.pop();
    } else {
      return false;
    }
    game.status = 'playing';
    game.message = null;
    return true;
  }

  function reset(game) {
    game.echoes = [];
    game.path = [{ ...game.level.start }];
    game.status = 'playing';
    game.message = null;
  }

  const api = {
    DIRS,
    parseLevel,
    createGame,
    now,
    echoPos,
    pressedPlates,
    doorStates,
    step,
    rewind,
    undo,
    reset,
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ParadoxeEngine = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
