/* La lucha. Este archivo solo orquesta: cada pregunta sobre el juego (jugadas legales,
 * volteos, pasos, final, qué juega el bot) se la hace al motor de Python por RB.engine.
 *
 * El tablero se construye UNA vez (64 botones) y cada ficha es un disco de dos caras: cambiar
 * data-color basta para que gire con una transición CSS. Aquí solo se calcula el retardo
 * (--delay) con el que gira cada ficha según su distancia a la jugada.
 *
 * Cada bando tiene su cartel de «Se busca»: un bot enseña a su personaje y una persona enseña
 * al pirata de pixel art con su nombre y su recompensa. Los selectores de arriba siempre están
 * activos: se puede cambiar de jugadores y empezar otra partida en cualquier momento, y también
 * poner dos bots a pelear entre ellos.
 *
 * Calaveras = negras = color 1 (mueven primero). Sombreros de paja = blancas = color -1.
 */
(function () {
  "use strict";

  const RB = window.RB;
  const h = RB.h;
  const crew = RB.crew;
  const $ = (id) => document.getElementById(id);
  const STORE_GAME = "bb-partida";
  const STORE_PREFS = "bb-ajustes";
  const BOT_DELAY_MS = 650;
  const PASS_DELAY_MS = 1400;
  const BOT_TIMEOUT_MS = 20000;
  const COLORS = [1, -1];
  const SIDE = { 1: "calaveras", "-1": "sombreros" };
  const COLS = "abcdefgh";
  const WORD = { 1: "calavera", "-1": "sombrero", 0: "vacía" };
  const INITIAL = Array.from({ length: 8 }, (_, r) => Array.from({ length: 8 }, (_, c) => (r === 3 && c === 3) || (r === 4 && c === 4) ? -1 : (r === 3 && c === 4) || (r === 4 && c === 3) ? 1 : 0));
  const CORNERS = ["0,0", "0,7", "7,0", "7,7"];

  const game = { token: 0, phase: "setup", players: [], seats: { 1: { kind: "human" }, "-1": { kind: "human" } }, seed: 0, view: null, busy: false, lastBot: null, focus: "3,3" };
  const ui = {};
  const cells = [];

  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const message = (e) => (e && e.message ? e.message : String(e));
  const key = (m) => m[0] + "," + m[1];
  function store(k, v) { try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* ok */ } }
  function load(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } }

  // ----------------------------------------------------------- asientos --- //

  const isHuman = (c) => game.seats[c].kind === "human";
  const botOf = (c) => (isHuman(c) ? null : game.seats[c].bot);
  const humanCount = () => COLORS.filter(isHuman).length;
  const botCount = () => 2 - humanCount();

  function label(c) {
    if (!isHuman(c)) return botOf(c).name;
    return humanCount() === 1 ? "Tú" : "Los " + SIDE[c];
  }

  function seatOf(value) {
    if (value === "human") return { kind: "human" };
    const bot = game.players.find((p) => p.name === value);
    return bot ? { kind: "bot", bot: bot } : { kind: "human" };
  }
  function selection() { const s = {}; COLORS.forEach((c) => { s[c] = seatOf(ui.seat[c].value); }); return s; }
  function savedSeats() { return { "1": isHuman(1) ? null : botOf(1).name, "-1": isHuman(-1) ? null : botOf(-1).name }; }
  const sameSeat = (a, b) => a.kind === b.kind && (a.kind === "human" || a.bot === b.bot);

  // ------------------------------------------------------------ el tablero --- //

  function buildBoard() {
    const grid = ui.board;
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const disc = h("span", { class: "disc", dataset: { color: "0" } }, h("span", { class: "face face--hat" }), h("span", { class: "face face--skull" }));
        const cell = h("button", { class: "cell", type: "button", tabindex: "-1", dataset: { r: String(r), c: String(c) }, "aria-disabled": "true" }, disc);
        cells.push({ cell: cell, disc: disc });
        grid.append(cell);
      }
    }
    grid.addEventListener("click", (e) => {
      const cell = e.target.closest(".cell");
      if (cell && cell.dataset.playable !== undefined) onPick([Number(cell.dataset.r), Number(cell.dataset.c)]);
    });
    grid.addEventListener("focusin", (e) => { const cell = e.target.closest(".cell"); if (cell) game.focus = cell.dataset.r + "," + cell.dataset.c; });
    grid.addEventListener("keydown", (e) => {
      const steps = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
      const step = steps[e.key]; const cell = e.target.closest(".cell");
      if (!step || !cell) return;
      e.preventDefault();
      const r = Math.min(7, Math.max(0, Number(cell.dataset.r) + step[0]));
      const c = Math.min(7, Math.max(0, Number(cell.dataset.c) + step[1]));
      cells.forEach((x) => { x.cell.tabIndex = -1; });
      const next = cells[r * 8 + c].cell; next.tabIndex = 0; next.focus();
    });
  }

  const gridHasFocus = () => ui.board.contains(document.activeElement);

  function paintBoard(view, animate) {
    const board = view ? view.state.board : INITIAL;
    const humanTurn = game.phase === "playing" && !!view && !view.over && isHuman(view.turn) && !game.busy;
    const legal = new Set(humanTurn ? view.legal.map(key) : []);
    const last = view && view.move ? key(view.move) : null;
    const flipped = new Set(animate && view ? (view.flipped || []).map(key) : []);
    if (!legal.has(game.focus) && legal.size && !gridHasFocus()) game.focus = legal.values().next().value;
    ui.chart.dataset.human = humanTurn ? String(view.turn) : "";
    ui.chart.dataset.wait = String(!humanTurn && game.phase === "playing");

    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const k = r + "," + c;
        const { cell, disc } = cells[r * 8 + c];
        const color = board[r][c];
        const dist = last ? Math.max(Math.abs(view.move[0] - r), Math.abs(view.move[1] - c)) : 1;
        disc.style.setProperty("--delay", flipped.has(k) ? 90 + (dist - 1) * 60 + "ms" : "0ms");
        if (animate && k === last) disc.dataset.pop = ""; else delete disc.dataset.pop;
        if (flipped.has(k)) disc.dataset.flip = ""; else delete disc.dataset.flip;
        disc.dataset.color = String(color);
        const playable = legal.has(k);
        if (playable) cell.dataset.playable = ""; else delete cell.dataset.playable;
        if (k === last) cell.dataset.last = ""; else delete cell.dataset.last;
        cell.tabIndex = k === game.focus ? 0 : -1;
        cell.setAttribute("aria-disabled", playable ? "false" : "true");
        cell.setAttribute("aria-label", COLS[c] + (r + 1) + ", " + WORD[color] + (playable ? ", jugada posible" : "") + (k === last ? ", última jugada" : ""));
      }
    }
  }

  // --------------------------------------------------------------- textos --- //

  function setStatus(state, text) { ui.status.dataset.state = state; ui.statusText.textContent = text; }

  let toastTimer = null;
  function toast(text) {
    clearTimeout(toastTimer);
    ui.toast.textContent = text; ui.toast.hidden = false;
    toastTimer = setTimeout(() => { ui.toast.hidden = true; }, PASS_DELAY_MS + 900);
  }

  function shout(text) {
    ui.sfx.textContent = text;
    ui.sfx.classList.remove("go"); void ui.sfx.offsetWidth; ui.sfx.classList.add("go");
  }

  /* Un bot habla desde el cartel de su bando; una persona no habla. */
  const sayTimers = {}, moodTimers = {};
  function say(kind, color) {
    const bot = botOf(color);
    if (!bot || game.phase === "setup") return;
    const box = $("say-" + color);
    box.hidden = false;
    box.textContent = crew.line(bot, kind);
    box.classList.remove("pop"); void box.offsetWidth; box.classList.add("pop");
    clearTimeout(sayTimers[color]);
    sayTimers[color] = setTimeout(() => { box.hidden = true; }, kind === "think" ? 2600 : 4200);
  }
  function mood(color, m, ms) {
    const card = $("rcard-" + color);
    card.dataset.mood = m;
    clearTimeout(moodTimers[color]);
    if (ms) moodTimers[color] = setTimeout(() => { card.dataset.mood = "neutral"; }, ms);
  }
  function quiet() {
    COLORS.forEach((c) => { clearTimeout(sayTimers[c]); $("say-" + c).hidden = true; mood(c, "neutral", 0); });
  }

  function turnText(c) {
    if (!isHuman(c)) return botOf(c).name + " está pensando…";
    return humanCount() === 1 ? "Te toca. Elige una casilla marcada con la brújula." : "Turno de los " + SIDE[c] + ".";
  }

  // ------------------------------------------------------------- carteles --- //

  /* Lo que enseña el cartel de un bando: un bot con su personaje, o una persona con el pirata de pixel art. */
  function posterData(color, seat, people) {
    if (seat.kind === "bot") {
      const p = crew.persona(seat.bot);
      return { key: "b:" + seat.bot.name, bot: seat.bot, persona: null, aka: p.aka, name: seat.bot.name, bounty: crew.fmt(p.bounty), foot: "" };
    }
    const prof = crew.profile;
    if (people === 1) {
      const r = crew.rank(prof.berries);
      return { key: "h:" + prof.name + ":" + prof.berries, bot: { icon: "👤", name: "Tú" }, persona: crew.LUFFY, aka: r.title, name: prof.name || "Capitán Anónimo", bounty: crew.fmt(prof.berries), foot: "" };
    }
    return { key: "h2:" + color, bot: { icon: "👤", name: "Persona" }, persona: crew.LUFFY, aka: "CAPITÁN " + (color === 1 ? "CALAVERA" : "SOMBRERO"), name: color === 1 ? "Jugador 1" : "Jugador 2", bounty: "—", foot: "" };
  }

  const shownPoster = {};
  function renderPosters(seats) {
    const people = COLORS.filter((c) => seats[c].kind === "human").length;
    COLORS.forEach((c) => {
      const d = posterData(c, seats[c], people);
      if (shownPoster[c] === d.key) return;
      shownPoster[c] = d.key;
      RB.fillPic($("pp-" + c + "-pic"), d.bot, "🏴‍☠️", d.persona);
      $("pp-" + c + "-aka").textContent = d.aka.toUpperCase();
      $("pp-" + c + "-name").textContent = d.name;
      $("pp-" + c + "-bounty").textContent = d.bounty;
      $("pp-" + c + "-foot").textContent = c === 1 ? "Bando de las calaveras" : "Bando de los sombreros";
    });
  }
  RB.refreshPosters = function () { shownPoster[1] = shownPoster[-1] = null; if (ui.board) renderPosters(game.phase === "setup" ? selection() : game.seats); };

  // --------------------------------------------------------------- render --- //

  const lastScore = [2, 2];
  function render(animate) {
    const view = game.view;
    paintBoard(view, animate);
    const playing = game.phase === "playing";
    const seats = game.phase === "setup" ? selection() : game.seats;
    const people = COLORS.filter((c) => seats[c].kind === "human").length;
    const score = view ? view.score : [2, 2];
    COLORS.forEach((c, i) => {
      const s = seats[c];
      $("cn-" + c).textContent = s.kind === "bot" ? s.bot.icon + " " + s.bot.name : people === 1 ? "👤 Tú" : "👤 Jugador " + (c === 1 ? 1 : 2);
      const n = $("cs-" + c);
      n.textContent = String(score[i]);
      if (score[i] !== lastScore[i]) { n.classList.remove("bump"); void n.offsetWidth; n.classList.add("bump"); lastScore[i] = score[i]; }
      $("cc-" + c).dataset.turn = String(playing && !!view && !view.over && view.turn === c);
    });
    const total = score[0] + score[1] || 1;
    $("m-sk").style.flexBasis = (score[0] / total) * 100 + "%";
    $("m-ht").style.flexBasis = (score[1] / total) * 100 + "%";
    ui.intro.hidden = game.phase !== "setup";
    renderPosters(seats);
    syncAgain();
  }

  /* El botón de siempre: dice «con los cambios» si lo elegido arriba ya no es lo que se está jugando. */
  function syncAgain() {
    const sel = game.players.length ? selection() : null;
    const changed = !!sel && game.phase !== "setup" && !COLORS.every((c) => sameSeat(sel[c], game.seats[c]));
    ui.again.textContent = changed ? "Nueva partida con los cambios" : "Nueva partida";
    ui.again.dataset.changed = String(changed);
  }

  function addLog(text, extra) {
    const li = h("li", {}, h("span", { text: text }), extra ? h("em", { text: extra }) : null);
    if (ui.log.firstElementChild && ui.log.firstElementChild.classList.contains("empty")) ui.log.replaceChildren();
    ui.log.prepend(li);
  }

  // ------------------------------------------------------------- resultado --- //

  function outcomeForHuman(view) {
    if (view.winner === 0) return "draw";
    return isHuman(view.winner) ? "win" : "lose";
  }

  function showResult() {
    const view = game.view;
    const solo = humanCount() === 1;
    let title;
    if (view.winner === 0) title = "¡Empate!";
    else if (solo) title = outcomeForHuman(view) === "win" ? "¡Victoria!" : "Derrota";
    else if (humanCount() === 2) title = "Ganan los " + SIDE[view.winner];
    else title = "Gana " + label(view.winner);
    $("res-title").textContent = title;
    $("res-score").textContent = "Calaveras " + view.score[0] + " – " + view.score[1] + " Sombreros";
    $("res-reason").hidden = !view.forfeit;
    $("res-reason").textContent = view.forfeit ? "Ha perdido por incumplir las reglas: " + view.forfeit + "." : "";
    const earn = $("res-earn");
    earn.hidden = true;
    if (solo && botCount() === 1) {
      const out = outcomeForHuman(view);
      const bot = COLORS.map(botOf).find(Boolean);
      const gained = RB.recordResult(bot, out, view.score[0] - view.score[1]);
      earn.hidden = false;
      $("res-earn-txt").textContent = out === "win" ? "Tu recompensa sube" : out === "draw" ? "Reparto del botín" : "Esta vez no hay botín";
      $("res-earn-n").textContent = (gained ? "+" : "") + crew.fmt(gained) + " berries";
      if (out === "win") RB.renderProfile(true);
      RB.refreshPosters();
    }
    ui.result.hidden = false;
    $("rematch").focus({ preventScroll: true });
  }

  // ---------------------------------------------------------------- partida --- //

  async function newGame() {
    if (!game.players.length) return;
    const token = ++game.token;
    Object.assign(game, { phase: "playing", seats: selection(), busy: true, seed: Math.floor(Math.random() * 2 ** 31), lastBot: null });
    ui.result.hidden = true; ui.toast.hidden = true;
    ui.log.replaceChildren(h("li", { class: "empty", text: "Aún no se ha movido ninguna ficha." }));
    quiet();
    setStatus("loading", "Preparando la partida…");
    try {
      const names = savedSeats();
      await RB.engine.call("start_match", [names["1"], names["-1"], game.seed]);
      const view = await RB.engine.call("new_game");
      if (token !== game.token) return;
      game.view = view;
    } catch (err) {
      if (token === game.token) failed("No se pudo empezar la partida: " + message(err));
      return;
    }
    save(); render(false);
    COLORS.forEach((c, i) => setTimeout(() => { if (token === game.token) say("hello", c); }, i * 500));
    continueGame(token);
  }

  function announcePass(view) {
    const passer = -view.mover;
    RB.sound.play("pass");
    toast(label(passer) + (isHuman(passer) && humanCount() === 1 ? ": no tienes jugadas posibles, pasas." : " no tiene jugada y pasa."));
    addLog(label(passer) + " pasa");
  }

  async function continueGame(token) {
    const view = game.view;
    if (view.over) return finish();
    if (view.passed) {
      announcePass(view);
      if (!isHuman(view.turn)) await wait(PASS_DELAY_MS);
      if (token !== game.token) return;
    }
    if (isHuman(view.turn)) {
      game.busy = false; render(false);
      setStatus("you", turnText(view.turn));
    } else {
      botTurn(token, view.turn);
    }
  }

  /* Efectos de una jugada ya pintada: sonido, diario, gritos y la reacción del rival. */
  function afterMove(view, color) {
    const n = view.flipped.length;
    addLog(label(color) + ": " + view.notation, "+" + n);
    RB.sound.play("move", { flips: n });
    if (CORNERS.includes(key(view.move))) shout("¡TESORO!");
    else if (n >= 5) shout(["¡GOMU GOMU!", "¡BOOM!", "¡ZAS!"][view.move[0] % 3]);
    else if (n >= 3) shout("¡ZAS!");
    if (n >= 4 && !isHuman(-color)) { say("big", -color); mood(-color, "surprised", 1200); }
    else if (!isHuman(color) && Math.random() < 0.4) say("move", color);
  }

  function onPick(move) {
    if (game.busy || game.phase !== "playing" || !game.view || !isHuman(game.view.turn)) return;
    const token = game.token;
    const color = game.view.turn;
    game.busy = true;
    RB.engine.call("play_move", [game.view.state, move]).then((view) => {
      if (token !== game.token) return;
      game.view = view; save(); render(true);
      afterMove(view, color);
      continueGame(token);
    }, (err) => {
      if (token !== game.token) return;
      game.busy = false; render(false);
      setStatus("error", "No se pudo hacer la jugada: " + message(err));
    });
  }

  async function botTurn(token, color) {
    const bot = botOf(color);
    game.busy = true; game.lastBot = color;
    render(false);
    setStatus("thinking", turnText(color));
    mood(color, "think", 0);
    if (Math.random() < 0.5) say("think", color);
    await wait(BOT_DELAY_MS);
    if (token !== game.token) return;
    let view;
    try {
      view = await RB.engine.call("bot_move", [game.view.state], { timeout: BOT_TIMEOUT_MS });
    } catch (err) {
      if (token !== game.token) return;
      mood(color, "neutral", 0);
      if (err.code === "timeout") {
        game.view = Object.assign({}, game.view, { over: true, turn: null, legal: [], winner: -color, move: null, flipped: [], forfeit: bot.name + " no respondió en " + BOT_TIMEOUT_MS / 1000 + " s" });
        return finish();
      }
      return failed("El motor no pudo mover a " + bot.name + ": " + message(err));
    }
    if (token !== game.token) return;
    mood(color, "neutral", 0);
    game.view = view; save(); render(!view.forfeit);
    if (!view.forfeit) afterMove(view, color);
    continueGame(token);
  }

  function finish() {
    game.phase = "over"; game.busy = false;
    store(STORE_GAME, null);
    render(false);
    const view = game.view;
    setStatus("over", view.forfeit ? "Un bot ha perdido por incumplir las reglas." : "Fin de la partida. Puedes cambiar de jugadores o empezar otra.");
    showResult();
    const solo = humanCount() === 1;
    let snd = "draw";
    if (view.winner !== 0) snd = solo && !isHuman(view.winner) ? "lose" : "win";
    RB.sound.play(snd);
    // Cada bot celebra o se lamenta según haya ganado su bando.
    COLORS.forEach((c) => {
      if (isHuman(c)) return;
      if (view.forfeit && view.winner === -c) { say("forfeit", c); mood(c, "sad", 1800); }
      else if (view.winner === 0) { say("draw", c); mood(c, "surprised", 1500); }
      else if (view.winner === c) { say("win", c); mood(c, "happy", 1800); }
      else { say("lose", c); mood(c, "sad", 1800); }
    });
    if (view.winner !== 0 && !view.forfeit) shout(solo ? (isHuman(view.winner) ? "¡VICTORIA!" : "¡DERROTA!") : "¡FIN!");
  }

  function failed(text) {
    game.phase = "over"; game.busy = false;
    store(STORE_GAME, null); render(false);
    setStatus("error", text + " Pulsa «Nueva partida» para intentarlo de nuevo.");
  }

  // ------------------------------------------------- guardar y recuperar --- //

  function save() {
    if (game.phase !== "playing" || !game.view || game.view.over) return store(STORE_GAME, null);
    store(STORE_GAME, { v: 1, seats: savedSeats(), seed: game.seed, state: game.view.state, last: game.view.move || null });
  }

  async function resume() {
    const saved = load(STORE_GAME);
    if (!saved || saved.v !== 1 || !saved.seats) { store(STORE_GAME, null); return false; }
    const seats = {};
    for (const c of COLORS) {
      const name = saved.seats[String(c)];
      if (name === null) seats[c] = { kind: "human" };
      else {
        const bot = game.players.find((p) => p.name === name);
        if (!bot) { store(STORE_GAME, null); return false; }
        seats[c] = { kind: "bot", bot: bot };
      }
    }
    const token = ++game.token;
    Object.assign(game, { phase: "playing", seats: seats, seed: saved.seed, busy: true, lastBot: null });
    try {
      await RB.engine.call("start_match", [saved.seats["1"], saved.seats["-1"], saved.seed]);
      const view = await RB.engine.call("view", [saved.state]);
      if (token !== game.token) return true;
      if (view.over) throw new Error("la partida guardada ya había terminado");
      game.view = Object.assign(view, { move: saved.last });
    } catch (err) {
      store(STORE_GAME, null);
      Object.assign(game, { phase: "setup", busy: false, view: null });
      return false;
    }
    COLORS.forEach((c) => { ui.seat[c].value = isHuman(c) ? "human" : botOf(c).name; });
    render(false);
    toast("Hemos recuperado tu partida.");
    continueGame(token);
    return true;
  }

  // ------------------------------------------------------------ preparación --- //

  function fillSeats(players, choice) {
    COLORS.forEach((c) => {
      const select = ui.seat[c];
      select.replaceChildren(h("option", { value: "human", text: "👤  Tú" }), ...players.map((p) => h("option", { value: p.name, text: p.icon + "  " + p.name })));
      select.value = choice[c];
      select.disabled = false;
    });
  }

  function onSeatChange() {
    const s = selection();
    store(STORE_PREFS, { "1": s[1].kind === "human" ? "human" : s[1].bot.name, "-1": s[-1].kind === "human" ? "human" : s[-1].bot.name });
    if (game.phase === "setup") render(false); else syncAgain();
  }

  function defaultChoice(prefs) {
    const ok = (v) => v === "human" || game.players.some((p) => p.name === v);
    const first = game.players[0] ? game.players[0].name : "human";
    return { 1: ok(prefs && prefs["1"]) ? prefs["1"] : first, "-1": ok(prefs && prefs["-1"]) ? prefs["-1"] : "human" };
  }

  async function onReady(info) {
    game.players = info.players;
    ui.retry.hidden = true;
    if (!game.players.length) { setStatus("error", "No hay rivales: añade un bot a players/."); return; }
    fillSeats(game.players, defaultChoice(load(STORE_PREFS)));
    ui.start.disabled = false; ui.again.disabled = false;
    ui.start.textContent = "¡Luchar!";
    $("intro-hint").textContent = "Por defecto llevas los sombreros de paja y el rival, las calaveras.";
    render(false);
    if (game.phase === "playing") return;
    if (await resume()) return;
    if (game.phase !== "setup") return;
    game.view = await RB.engine.call("new_game").catch(() => null);
    render(false);
    setStatus("idle", "Elige quién pelea con cada bandera y pulsa «¡Luchar!».");
  }

  function onFatal(error) {
    ui.start.disabled = true; ui.again.disabled = true; ui.start.textContent = "Motor no disponible";
    COLORS.forEach((c) => { ui.seat[c].disabled = true; });
    setStatus("error", "No se pudo arrancar el motor de Python: " + error);
    $("intro-hint").textContent = "Sin el motor no hay partida. Abre la web con un servidor local (python -m http.server) y con conexión.";
    ui.retry.hidden = false;
  }

  function init() {
    Object.assign(ui, {
      chart: $("chart"), board: $("board"), toast: $("toast"), sfx: $("sfx"), status: $("status"), statusText: $("status-text"),
      intro: $("intro"), result: $("result"), start: $("start"), again: $("again"), retry: $("retry"), log: $("logbook"),
      seat: { 1: $("seat-1"), "-1": $("seat--1") },
    });
    buildBoard();
    render(false);
    COLORS.forEach((c) => ui.seat[c].addEventListener("change", onSeatChange));
    ui.start.addEventListener("click", newGame);
    ui.again.addEventListener("click", newGame);
    $("rematch").addEventListener("click", newGame);
    $("change").addEventListener("click", () => { ui.result.hidden = true; ui.seat[1].focus(); });
    ui.retry.addEventListener("click", () => { ui.retry.hidden = true; setStatus("loading", "Reintentando…"); RB.engine.restart(); });
    RB.engine.on("status", (t) => { if (game.phase === "setup" && !game.players.length) setStatus("loading", t); });
    RB.engine.on("ready", (info) => { onReady(info).catch(RB.reportError); });
    RB.engine.on("fatal", onFatal);
  }

  /* Desde el tablón de rivales: tú con los sombreros y ese rival con las calaveras. */
  RB.play = {
    challenge(name) {
      if (!game.players.some((p) => p.name === name)) return;
      ui.seat[1].value = name; ui.seat[-1].value = "human";
      onSeatChange();
    },
  };

  init();
})();
