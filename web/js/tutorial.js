/* Aprende jugando: lecciones cortas con el mentor, sobre el mismo tablero que «Lucha».
 *
 * Las lecciones son datos (data/tutorial.json): la posición de partida y, en orden, las jugadas
 * del jugador y del rival con la frase del mentor. Este archivo solo las representa:
 *
 * - El jugador lleva siempre las calaveras. En una lección «guion», la ÚNICA casilla que se
 *   puede pulsar es la que toca: las demás no responden, ni con el ratón ni con el teclado.
 * - Las reglas no se calculan aquí: el motor de Python dice qué es legal (view) y aplica cada
 *   jugada (play_move), igual que en una partida. Si una lección pidiera una jugada ilegal, la
 *   página lo dice en vez de quedarse atascada (y los tests lo impiden antes de publicarla).
 * - Cada lección es una partida independiente: al terminar, «Siguiente lección» salta a la
 *   posición de la siguiente. Las lecciones ya vistas se pueden repetir desde la lista.
 * - Los textos vienen de un archivo: entran como texto (RB.h usa textContent), nunca como HTML.
 *
 *   RB.tutorial.enter()   se llama al entrar en #/aprende
 */
(function () {
  "use strict";

  const RB = (window.RB = window.RB || {});
  const FILE = "data/tutorial.json";
  const VERSION = 1;
  const STORE = "bb-tutorial";
  const RIVAL_DELAY_MS = 900;
  const PIECE = { X: 1, O: -1, ".": 0 };
  const COLS = "abcdefgh";
  const WORD = { 1: "calavera", "-1": "sombrero", 0: "vacía" };

  const $ = (id) => document.getElementById(id);
  const h = (...args) => RB.h(...args);
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const key = (m) => m[0] + "," + m[1];
  const toMove = (text) => [Number(text[1]) - 1, COLS.indexOf(text[0])];

  const tut = { lessons: null, index: 0, step: 0, view: null, forced: null, busy: false, token: 0, seen: 0, started: false };
  const cells = [];

  function readSeen() { try { return Number(localStorage.getItem(STORE)) || 0; } catch (e) { return 0; } }
  function saveSeen() { try { localStorage.setItem(STORE, String(tut.seen)); } catch (e) { /* sin almacenamiento: se juega igual */ } }

  // ------------------------------------------------------------ el tablero --- //

  function buildBoard() {
    const grid = $("tut-board");
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
  }

  /* Solo la casilla obligada lleva la brújula y responde; el resto del tablero, solo se mira. */
  function paint(animate) {
    const view = tut.view;
    const forced = tut.forced && !tut.busy ? key(tut.forced) : null;
    const last = view && view.move ? key(view.move) : null;
    const flipped = new Set(animate && view ? (view.flipped || []).map(key) : []);
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const k = r + "," + c;
        const { cell, disc } = cells[r * 8 + c];
        const color = view ? view.state.board[r][c] : 0;
        const dist = last ? Math.max(Math.abs(view.move[0] - r), Math.abs(view.move[1] - c)) : 1;
        disc.style.setProperty("--delay", flipped.has(k) ? 90 + (dist - 1) * 60 + "ms" : "0ms");
        if (animate && k === last) disc.dataset.pop = ""; else delete disc.dataset.pop;
        if (flipped.has(k)) disc.dataset.flip = ""; else delete disc.dataset.flip;
        disc.dataset.color = String(color);
        const playable = k === forced;
        if (playable) cell.dataset.playable = ""; else delete cell.dataset.playable;
        if (k === last) cell.dataset.last = ""; else delete cell.dataset.last;
        cell.tabIndex = playable ? 0 : -1;
        cell.setAttribute("aria-disabled", playable ? "false" : "true");
        cell.setAttribute("aria-label", COLS[c] + (r + 1) + ", " + WORD[color] + (playable ? ", juega aquí" : "") + (k === last ? ", última jugada" : ""));
      }
    }
    const score = view ? view.score : [0, 0];
    $("tut-score").textContent = "Calaveras " + score[0] + " · Sombreros " + score[1];
  }

  // ---------------------------------------------------------------- textos --- //

  /* El bocadillo del mentor. «who» le da el color (tu | rival | fin | error) y las casillas que
   * nombra (f5, d6…) salen resaltadas para encontrarlas en el tablero. Todo entra como texto. */
  function say(text, who) {
    const box = $("tut-say");
    const parts = text ? String(text).split(/\b([a-h][1-8])\b/) : [];
    box.replaceChildren(...parts.filter(Boolean).map((p) => (/^[a-h][1-8]$/.test(p) ? h("b", { text: p }) : p)));
    box.dataset.who = who || "";
    box.classList.remove("pop");
    void box.offsetWidth;
    if (text) box.classList.add("pop");
  }

  function actions(...buttons) { $("tut-actions").replaceChildren(...buttons.filter(Boolean)); }

  function button(text, onclick, cls) { return h("button", { class: "btn btn--sm" + (cls ? " " + cls : ""), type: "button", onclick: onclick, text: text }); }

  function renderLessons() {
    const list = $("tut-lessons");
    list.replaceChildren(...tut.lessons.map((lesson, i) => h("li", null,
      h("button", {
        class: "tut__lesson", type: "button", dataset: { state: i === tut.index ? "now" : i < tut.seen ? "done" : "locked" },
        disabled: i > tut.seen, "aria-current": i === tut.index ? "step" : null,
        onclick: () => startLesson(i),
      }, h("b", { text: String(i + 1) }), h("span", { text: lesson.title })),
    )));
    $("tut-progress").textContent = "Lección " + (tut.index + 1) + " de " + tut.lessons.length;
    $("tut-title").textContent = tut.lessons[tut.index].title;
  }

  function fail(text) {
    tut.busy = false; tut.forced = null;
    say(text, "error");
    actions(button("Reintentar", () => startLesson(tut.index)));
    if (tut.view) paint(false);
  }

  // -------------------------------------------------------------- lecciones --- //

  /* La posición de un archivo de texto al formato del motor; el motor la valida (view). */
  function stateOf(lesson) {
    return { board: lesson.board.map((row) => Array.from(row).map((ch) => PIECE[ch])), player: PIECE[lesson.to_move] };
  }

  async function startLesson(i) {
    const token = ++tut.token;
    const lesson = tut.lessons[i];
    Object.assign(tut, { index: i, step: 0, forced: null, busy: true });
    renderLessons();
    $("tut-intro").textContent = lesson.intro;
    say("");
    actions();
    try {
      const view = await RB.engine.call("view", [stateOf(lesson)]);
      if (token !== tut.token) return;
      tut.view = view;
    } catch (err) {
      if (token === tut.token) fail("No se pudo preparar la lección: " + (err && err.message ? err.message : err));
      return;
    }
    paint(false);
    next(token);
  }

  /* El siguiente paso del guion: esperar la jugada del jugador o hacer la del rival. */
  async function next(token) {
    const lesson = tut.lessons[tut.index];
    const step = lesson.steps[tut.step];
    if (!step) return finishLesson();
    const move = toMove(step.move);
    const turn = step.who === "tu" ? 1 : -1;
    if (tut.view.turn !== turn || !tut.view.legal.some((m) => key(m) === key(move))) {
      return fail("Esta lección está mal preparada: " + step.move + " no se puede jugar ahora.");
    }
    say(step.say, step.who);
    if (step.who === "tu") {
      tut.forced = move; tut.busy = false;
      paint(false);
      return;
    }
    // El rival juega y la partida se para: el jugador lee la frase y decide cuándo seguir.
    tut.busy = true; tut.forced = null;
    paint(false);
    await wait(RIVAL_DELAY_MS);
    if (token !== tut.token || !(await play(token, move))) return;
    await continuePressed(token);
    if (token === tut.token) next(token);
  }

  function onPick(move) {
    if (tut.busy || !tut.forced || key(move) !== key(tut.forced)) return;
    const token = tut.token;
    tut.busy = true; tut.forced = null;
    play(token, move).then((ok) => { if (ok && token === tut.token) next(token); });
  }

  /* Aplica una jugada con el motor y la pinta. Devuelve true si se ha podido. */
  async function play(token, move) {
    try {
      const view = await RB.engine.call("play_move", [tut.view.state, move]);
      if (token !== tut.token) return false;
      tut.view = view;
    } catch (err) {
      if (token === tut.token) fail("No se pudo hacer la jugada: " + (err && err.message ? err.message : err));
      return false;
    }
    paint(true);
    if (RB.sound) RB.sound.play("move", { flips: tut.view.flipped.length });
    tut.step++;
    $("tut-intro").textContent = "";  // la bienvenida solo se ve antes de la primera jugada
    return true;
  }

  /* Espera a que el jugador pulse «Continuar» o haga clic en el tablero. */
  function continuePressed(token) {
    return new Promise((resolve) => {
      const done = () => {
        $("tut-chart").removeEventListener("click", done);
        if (token === tut.token) actions();
        resolve();
      };
      const btn = button("Continuar ▸", done, "btn--gold");
      actions(btn);
      btn.focus({ preventScroll: true });
      $("tut-chart").addEventListener("click", done);
    });
  }

  function finishLesson() {
    const lesson = tut.lessons[tut.index];
    const last = tut.index === tut.lessons.length - 1;
    tut.busy = false; tut.forced = null;
    tut.seen = Math.max(tut.seen, tut.index + 1);
    saveSeen();
    renderLessons();
    paint(false);
    say(lesson.done, "fin");
    if (RB.sound) RB.sound.play("win");
    actions(
      last ? null : button("Siguiente lección", () => startLesson(tut.index + 1), "btn--gold"),
      button("Repetir la lección", () => startLesson(tut.index), "btn--paper"),
      last ? h("a", { class: "btn btn--sm btn--gold", href: "#/jugar", text: "¡A luchar!" }) : null,
    );
  }

  // ------------------------------------------------------------------ inicio --- //

  async function load() {
    const res = await fetch(FILE, { cache: "no-cache" });
    if (!res.ok) throw new Error("no se encontró " + FILE + " (" + res.status + ")");
    const data = await res.json();
    if (!data || data.version !== VERSION || !Array.isArray(data.lessons) || !data.lessons.length) {
      throw new Error("el archivo de lecciones no tiene la forma esperada");
    }
    return data.lessons;
  }

  function whenEngineReady() {
    if (RB.engine.state === "ready") return Promise.resolve();
    if (RB.engine.state === "error") return Promise.reject(new Error(RB.engine.error));
    return new Promise((resolve, reject) => {
      RB.engine.on("ready", () => resolve());
      RB.engine.on("fatal", (msg) => reject(new Error(msg)));
      RB.engine.start();
    });
  }

  /* La primera vez que se entra, carga las lecciones y empieza por la primera sin terminar. */
  async function enter() {
    if (tut.started) return;
    tut.started = true;
    if (!cells.length) buildBoard();
    say("Cargando las lecciones y el motor de Python…");
    try {
      tut.lessons = await load();
      await whenEngineReady();
    } catch (err) {
      tut.started = false;
      say("No se pudo empezar el tutorial: " + (err && err.message ? err.message : err));
      actions(button("Reintentar", () => { if (RB.engine.state === "error") RB.engine.restart(); enter(); }));
      return;
    }
    tut.seen = Math.min(readSeen(), tut.lessons.length);
    startLesson(Math.min(tut.seen, tut.lessons.length - 1));
  }

  RB.tutorial = { enter: enter };
})();
