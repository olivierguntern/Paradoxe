/*
 * Paradoxe — interface navigateur : rendu du plateau, commandes, messages.
 */
(function () {
  'use strict';

  const E = window.ParadoxeEngine;
  const LEVELS = window.PARADOXE_LEVELS;
  const STORAGE_KEY = 'paradoxe.level';

  const COLORS = {
    floor: '#151a2e',
    grid: '#1c2340',
    wall: '#2a3152',
    wallEdge: '#39426b',
    start: '#b18cff',
    exit: '#4ce0a0',
    player: '#ffd36b',
    echo: '#5cc8ff',
    links: ['#f5a524', '#ff5fa2', '#7cf26b', '#5c8dff', '#ff7b4a', '#c38cff', '#3de0d0', '#ffe14d', '#ff4d6d'],
  };

  const canvas = document.getElementById('board');
  const ctx = canvas.getContext('2d');
  const $ = (id) => document.getElementById(id);

  let levelIndex = loadProgress();
  let game = null;
  let tile = 48;

  function loadProgress() {
    try {
      const i = parseInt(localStorage.getItem(STORAGE_KEY), 10);
      return Number.isInteger(i) && i >= 0 && i < LEVELS.length ? i : 0;
    } catch (e) {
      return 0;
    }
  }

  function saveProgress(i) {
    try {
      localStorage.setItem(STORAGE_KEY, String(i));
    } catch (e) {
      /* stockage indisponible : la progression n'est simplement pas conservée */
    }
  }

  function log(text, cls) {
    const li = document.createElement('li');
    li.textContent = text;
    if (cls) li.className = cls;
    const list = $('log');
    list.prepend(li);
    while (list.children.length > 30) list.lastChild.remove();
  }

  function loadLevel(i) {
    levelIndex = i;
    saveProgress(i);
    game = E.createGame(LEVELS[i]);
    $('level-title').textContent = `Niveau ${i + 1} — ${game.level.name}`;
    $('level-intro').textContent = game.level.intro;
    $('log').innerHTML = '';
    log(`Niveau ${i + 1} : ${game.level.name}`);
    resize();
  }

  /* ---------- Actions ---------- */

  function act(action) {
    if (!game) return;

    if (action === 'reset') {
      E.reset(game);
      log('Chronologie effacée.');
    } else if (action === 'undo') {
      if (E.undo(game)) log('Action annulée.');
    } else if (action === 'next') {
      if (game.status === 'won') loadLevel(Math.min(levelIndex + 1, LEVELS.length - 1));
      return;
    } else if (action === 'rewind') {
      const r = E.rewind(game);
      if (r.ok) log(`Retour au départ. Écho n°${r.echoes} créé.`, 'good');
      else log(r.reason, 'warn');
    } else {
      const r = E.step(game, action);
      if (r.type === 'blocked') {
        if (r.reason === 'echo') log('Un écho occupera cette case : passage impossible.', 'warn');
      } else if (r.type === 'paradox') {
        log('PARADOXE — ' + r.message, 'warn');
      } else if (r.type === 'won') {
        log('Sortie atteinte. Chronologie stable.', 'good');
      } else if (r.type === 'timeout') {
        log(`Temps écoulé : retour automatique. Écho n°${r.echoes} créé.`, 'warn');
      }
    }
    render();
  }

  /* ---------- Overlay ---------- */

  function showOverlay(kind, title, text, actions) {
    const el = $('overlay');
    el.className = 'overlay ' + kind;
    $('overlay-title').textContent = title;
    $('overlay-text').textContent = text;
    const box = $('overlay-actions');
    box.innerHTML = '';
    for (const [label, action, primary] of actions) {
      const b = document.createElement('button');
      b.textContent = label;
      b.dataset.action = action;
      if (primary) b.className = 'primary';
      box.appendChild(b);
    }
  }

  function hideOverlay() {
    $('overlay').className = 'overlay hidden';
  }

  function updateOverlay() {
    if (game.status === 'paradox') {
      showOverlay('paradox', 'Paradoxe', game.message, [
        ['Annuler (U)', 'undo', true],
        ['Recommencer (N)', 'reset'],
      ]);
    } else if (game.status === 'won') {
      const last = levelIndex === LEVELS.length - 1;
      const loops = game.echoes.length + 1;
      showOverlay(
        'won',
        last ? 'Chronologie restaurée' : 'Niveau terminé',
        `Résolu en ${loops} boucle${loops > 1 ? 's' : ''}.` +
          (last ? ' Fin de la démo : de nouveaux niveaux arrivent.' : ''),
        last
          ? [['Rejouer depuis le début', 'restart-all', true]]
          : [['Niveau suivant (Entrée)', 'next', true], ['Rejouer', 'reset']]
      );
    } else {
      hideOverlay();
    }
  }

  /* ---------- HUD ---------- */

  function updateHud() {
    const t = E.now(game);
    const T = game.level.timeLimit;
    $('stat-time').textContent = `${t} / ${T}`;
    $('stat-loop').textContent = `${game.echoes.length + 1} / ${game.level.maxEchoes + 1}`;
    $('stat-echoes').textContent = `${game.echoes.length} / ${game.level.maxEchoes}`;
    $('timebar-fill').style.width = `${(t / T) * 100}%`;

    const list = $('echo-list');
    list.innerHTML = '';
    game.echoes.forEach((echo, i) => {
      const li = document.createElement('li');
      const end = echo.length - 1;
      const gone = t > end;
      li.className = gone ? 'gone' : '';
      li.textContent = gone
        ? `Écho ${i + 1} — reparti dans le passé à t=${end}`
        : `Écho ${i + 1} — présent jusqu'à t=${end}`;
      list.appendChild(li);
    });
  }

  /* ---------- Rendu ---------- */

  function resize() {
    if (!game) return;
    const wrap = canvas.parentElement;
    const maxW = Math.max(200, wrap.clientWidth);
    tile = Math.max(20, Math.min(56, Math.floor(maxW / game.level.width)));
    const w = tile * game.level.width;
    const h = tile * game.level.height;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    render();
  }

  function linkColor(id) {
    return COLORS.links[(parseInt(id, 10) - 1) % COLORS.links.length];
  }

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function label(text, cx, cy, color, size) {
    ctx.fillStyle = color;
    ctx.font = `600 ${Math.round(size)}px system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, cx, cy + 1);
  }

  function drawTiles() {
    const L = game.level;
    for (let y = 0; y < L.height; y++) {
      for (let x = 0; x < L.width; x++) {
        const px = x * tile;
        const py = y * tile;
        if (L.walls.has(x + ',' + y)) {
          ctx.fillStyle = COLORS.wall;
          ctx.fillRect(px, py, tile, tile);
          ctx.fillStyle = COLORS.wallEdge;
          ctx.fillRect(px, py, tile, 3);
        } else {
          ctx.fillStyle = COLORS.floor;
          ctx.fillRect(px, py, tile, tile);
          ctx.strokeStyle = COLORS.grid;
          ctx.lineWidth = 1;
          ctx.strokeRect(px + 0.5, py + 0.5, tile - 1, tile - 1);
        }
      }
    }
  }

  function drawStartAndExit() {
    const L = game.level;
    const s = L.start;
    const cx = (s.x + 0.5) * tile;
    const cy = (s.y + 0.5) * tile;
    ctx.strokeStyle = COLORS.start;
    ctx.lineWidth = 2;
    for (const r of [0.38, 0.26]) {
      ctx.beginPath();
      ctx.arc(cx, cy, tile * r, 0, Math.PI * 2);
      ctx.stroke();
    }

    const e = L.exit;
    const ex = e.x * tile;
    const ey = e.y * tile;
    const grad = ctx.createRadialGradient(ex + tile / 2, ey + tile / 2, 2, ex + tile / 2, ey + tile / 2, tile / 2);
    grad.addColorStop(0, 'rgba(76,224,160,0.9)');
    grad.addColorStop(1, 'rgba(76,224,160,0.05)');
    ctx.fillStyle = grad;
    ctx.fillRect(ex + 2, ey + 2, tile - 4, tile - 4);
    label('⇲', ex + tile / 2, ey + tile / 2, '#0b0e1a', tile * 0.45);
  }

  function drawPlates(pressed) {
    for (const p of game.level.plates) {
      const color = linkColor(p.id);
      const on = pressed.has(p.id);
      const m = tile * 0.16;
      roundRect(p.x * tile + m, p.y * tile + m, tile - 2 * m, tile - 2 * m, 6);
      ctx.fillStyle = on ? color : 'rgba(0,0,0,0.25)';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();
      label(p.id, (p.x + 0.5) * tile, (p.y + 0.5) * tile, on ? '#0b0e1a' : color, tile * 0.32);
    }
  }

  function drawDoors(doors) {
    for (const d of doors) {
      const color = linkColor(d.id);
      const px = d.x * tile;
      const py = d.y * tile;
      if (d.open) {
        ctx.strokeStyle = color;
        ctx.globalAlpha = 0.6;
        ctx.setLineDash([4, 4]);
        ctx.lineWidth = 2;
        ctx.strokeRect(px + 4, py + 4, tile - 8, tile - 8);
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
      } else {
        ctx.fillStyle = color;
        ctx.fillRect(px + 2, py + 2, tile - 4, tile - 4);
        if (d.inverse) {
          ctx.save();
          ctx.beginPath();
          ctx.rect(px + 2, py + 2, tile - 4, tile - 4);
          ctx.clip();
          ctx.strokeStyle = 'rgba(11,14,26,0.55)';
          ctx.lineWidth = tile * 0.08;
          for (let k = -tile; k < tile * 2; k += tile * 0.25) {
            ctx.beginPath();
            ctx.moveTo(px + k, py);
            ctx.lineTo(px + k + tile, py + tile);
            ctx.stroke();
          }
          ctx.restore();
        }
      }
      label(d.inverse ? '¬' + d.id : d.id, px + tile / 2, py + tile / 2, d.open ? color : '#0b0e1a', tile * 0.3);
    }
  }

  function drawEchoes(t) {
    game.echoes.forEach((echo, i) => {
      const p = E.echoPos(echo, t);
      if (!p) return;
      const next = E.echoPos(echo, t + 1);
      if (next && (next.x !== p.x || next.y !== p.y) && game.status === 'playing') {
        ctx.strokeStyle = COLORS.echo;
        ctx.globalAlpha = 0.6;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc((next.x + 0.5) * tile, (next.y + 0.5) * tile, tile * 0.14, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
      ctx.fillStyle = COLORS.echo;
      ctx.globalAlpha = 0.55;
      ctx.beginPath();
      ctx.arc((p.x + 0.5) * tile, (p.y + 0.5) * tile, tile * 0.3, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
      label(String(i + 1), (p.x + 0.5) * tile, (p.y + 0.5) * tile, '#0b0e1a', tile * 0.3);
    });
  }

  function drawPlayer(t) {
    const p = game.path[t];
    const cx = (p.x + 0.5) * tile;
    const cy = (p.y + 0.5) * tile;
    ctx.shadowColor = COLORS.player;
    ctx.shadowBlur = 12;
    ctx.fillStyle = game.status === 'paradox' ? '#ff5c7a' : COLORS.player;
    ctx.beginPath();
    ctx.arc(cx, cy, tile * 0.32, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
  }

  function render() {
    if (!game) return;
    const t = E.now(game);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawTiles();
    drawStartAndExit();
    drawPlates(E.pressedPlates(game, t));
    drawDoors(E.doorStates(game, t));
    drawEchoes(t);
    drawPlayer(t);
    updateHud();
    updateOverlay();
  }

  /* ---------- Entrées ---------- */

  const KEYMAP = {
    ArrowUp: 'up',
    ArrowDown: 'down',
    ArrowLeft: 'left',
    ArrowRight: 'right',
    Space: 'wait',
    Backspace: 'undo',
    Enter: 'next',
  };

  // Les lettres sont lues via event.key (caractère tapé) et non event.code
  // (position physique) : ZQSD en AZERTY et WASD en QWERTY fonctionnent tous deux.
  const LETTERS = { z: 'up', w: 'up', s: 'down', q: 'left', a: 'left', d: 'right', r: 'rewind', u: 'undo', n: 'reset' };

  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const letter = e.key && e.key.length === 1 ? LETTERS[e.key.toLowerCase()] : undefined;
    const action = letter || KEYMAP[e.code];
    if (!action) return;
    e.preventDefault();
    act(action);
  });

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;
    const action = btn.dataset.action;
    if (action === 'restart-all') loadLevel(0);
    else act(action);
  });

  // Glisser sur le plateau (écran tactile) pour se déplacer, toucher pour attendre.
  let touchStart = null;
  canvas.addEventListener('pointerdown', (e) => {
    touchStart = { x: e.clientX, y: e.clientY };
  });
  canvas.addEventListener('pointerup', (e) => {
    if (!touchStart) return;
    const dx = e.clientX - touchStart.x;
    const dy = e.clientY - touchStart.y;
    touchStart = null;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < 24) return;
    if (Math.abs(dx) > Math.abs(dy)) act(dx > 0 ? 'right' : 'left');
    else act(dy > 0 ? 'down' : 'up');
  });

  window.addEventListener('resize', resize);

  loadLevel(levelIndex);
})();
