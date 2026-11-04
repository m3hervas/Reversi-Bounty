/* Aprende jugando: lecciones cortas con el mentor, sobre el mismo tablero que «Lucha».
 *
 * Las lecciones son datos (data/tutorial.json). Hay dos tipos:
 *
 * - «guion»: la posición de partida y, en orden, las jugadas del jugador y del rival con la frase del
 *   mentor. La ÚNICA casilla que se puede pulsar es la que toca: las demás no responden, ni con el
 *   ratón ni con el teclado. Un paso «volver» devuelve el tablero a la posición de partida.
 * - «libre»: una partida de verdad contra un bot del registro desde la posición de la lección. Se
 *   puede jugar cualquier jugada legal y, tras cada una, el mentor dice si ha sido buena o mala por
 *   las fichas que puede quitarte el rival en su respuesta. Si ganas, superas el tutorial; si no,
 *   puedes reintentarlo.
 *
 * El jugador lleva siempre las calaveras. Las reglas no se calculan aquí: el motor de Python dice qué
 * es legal (view), aplica cada jugada (play_move), valora las jugadas (coach) y mueve al bot
 * (bot_move), igual que en una partida. Los textos vienen de un archivo: entran como texto (RB.h usa
 * textContent), nunca como HTML.
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
  const BOT_TIMEOUT_MS = 20000;
  const PIECE = { X: 1, O: -1, ".": 0 };
  const COLS = "abcdefgh";
  const WORD = { 1: "calavera", "-1": "sombrero", 0: "vacía" };

  const $ = (id) => document.getElementById(id);
  const h = (...args) => RB.h(...args);
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const key = (m) => m[0] + "," + m[1];
  const toMove = (text) => [Number(text[1]) - 1, COLS.indexOf(text[0])];
  const message = (err) => (err && err.message ? err.message : String(err));
  const fichas = (n) => n + (n === 1 ? " ficha" : " fichas");

  /* allowed: las casillas que se pueden pulsar ahora (una sola en un guion; todas las legales en libre). */
  const tut = { lessons: null, index: 0, step: 0, view: null, allowed: new Set(), coach: null, advice: null, busy: false, token: 0, seen: 0, started: false, ready: false };
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

  /* Solo las casillas permitidas llevan la brújula y responden; el resto del tablero, solo se mira. */
  function paint(animate) {
    const view = tut.view;
    const allowed = tut.busy ? new Set() : tut.allowed;
    const last = view && view.move ? key(view.move) : null;
    const flipped = new Set(animate && view ? (view.flipped || []).map(key) : []);
    let first = true;
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
        const playable = allowed.has(k);
        if (playable) cell.dataset.playable = ""; else delete cell.dataset.playable;
        if (k === last) cell.dataset.last = ""; else delete cell.dataset.last;
        cell.tabIndex = playable && first ? 0 : -1;
        if (playable) first = false;
        cell.setAttribute("aria-disabled", playable ? "false" : "true");
        cell.setAttribute("aria-label", COLS[c] + (r + 1) + ", " + WORD[color] + (playable ? ", juega aquí" : "") + (k === last ? ", última jugada" : ""));
      }
    }
    const score = view ? view.score : [0, 0];
    $("tut-score").textContent = "Calaveras " + score[0] + " · Sombreros " + score[1];
  }

  // ---------------------------------------------------------------- textos --- //

  /* El bocadillo del mentor. «who» le da el color (tu | rival | volver | bien | mal | fin | error) y las
   * casillas que nombra (f5, d6…) salen resaltadas para encontrarlas en el tablero. Todo entra como texto. */
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
    tut.busy = false; tut.allowed = new Set();
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
    Object.assign(tut, { index: i, step: 0, allowed: new Set(), coach: null, advice: null, busy: true });
    renderLessons();
    $("tut-intro").textContent = lesson.intro;
    say("");
    actions();
    if (i === 0 && !(await welcome(token))) return;
    try {
      const view = await RB.engine.call("view", [stateOf(lesson)]);
      if (token !== tut.token) return;
      tut.view = view;
    } catch (err) {
      if (token === tut.token) fail("No se pudo preparar la lección: " + message(err));
      return;
    }
    paint(false);
    if (lesson.kind === "libre") startFree(token, lesson); else next(token);
  }

  /* La pantalla de bienvenida, antes de la lección 1: las lecciones aparecen una a una y el botón
   * «¡Zarpamos!» la cierra. Devuelve false si mientras tanto se ha empezado otra lección. */
  function welcome(token) {
    const box = $("tut-welcome");
    $("tut-welcome-list").replaceChildren(...tut.lessons.map((lesson, i) => h("li", { style: "--i:" + i },
      h("b", { text: String(i + 1) }), h("span", { text: lesson.title }))));
    box.hidden = false;
    const go = $("tut-welcome-go");
    go.focus({ preventScroll: true });
    return new Promise((resolve) => {
      go.onclick = () => {
        go.onclick = null;
        box.hidden = true;
        resolve(token === tut.token);
      };
    });
  }

  /* El siguiente paso del guion: esperar la jugada del jugador o hacer la del rival. */
  async function next(token) {
    const lesson = tut.lessons[tut.index];
    const step = lesson.steps[tut.step];
    if (!step) return finishLesson();
    if (step.who === "volver") return rewind(token, lesson, step);
    const move = toMove(step.move);
    const turn = step.who === "tu" ? 1 : -1;
    if (tut.view.turn !== turn || !tut.view.legal.some((m) => key(m) === key(move))) {
      return fail("Esta lección está mal preparada: " + step.move + " no se puede jugar ahora.");
    }
    say(step.say, step.who);
    if (step.who === "tu") {
      tut.allowed = new Set([key(move)]); tut.busy = false;  // solo la casilla obligada
      paint(false);
      return;
    }
    // El rival juega y la partida se para: el jugador lee la frase y decide cuándo seguir.
    tut.busy = true; tut.allowed = new Set();
    paint(false);
    await wait(RIVAL_DELAY_MS);
    if (token !== tut.token || !(await play(token, move))) return;
    await continuePressed(token);
    if (token === tut.token) next(token);
  }

  /* «Volver atrás»: el mentor explica el error sobre el tablero que ha quedado y, cuando el jugador
   * lo pide, la lección vuelve a su posición de partida para hacer la jugada buena. */
  async function rewind(token, lesson, step) {
    say(step.say, "volver");
    tut.busy = true; tut.allowed = new Set();
    paint(false);
    await continuePressed(token, "◂ Volver atrás");
    if (token !== tut.token) return;
    try {
      const view = await RB.engine.call("view", [stateOf(lesson)]);
      if (token !== tut.token) return;
      tut.view = view;
    } catch (err) {
      if (token === tut.token) fail("No se pudo volver atrás: " + message(err));
      return;
    }
    tut.step++;
    paint(false);
    if (RB.sound) RB.sound.play("pass");
    next(token);
  }

  function onPick(move) {
    if (tut.busy || !tut.allowed.has(key(move))) return;
    const token = tut.token;
    const free = tut.lessons[tut.index].kind === "libre";
    if (free) tut.advice = advise(move);
    tut.busy = true; tut.allowed = new Set();
    play(token, move).then((ok) => {
      if (!ok || token !== tut.token) return;
      if (!free) return next(token);
      const pass = tut.view.passed ? " El rival no puede mover y pasa: vuelves a jugar tú." : "";
      say(tut.advice.text + pass, tut.advice.who);
      freeTurn(token);
    });
  }

  /* Aplica una jugada con el motor y la pinta. Devuelve true si se ha podido. */
  async function play(token, move) {
    try {
      const view = await RB.engine.call("play_move", [tut.view.state, move]);
      if (token !== tut.token) return false;
      tut.view = view;
    } catch (err) {
      if (token === tut.token) fail("No se pudo hacer la jugada: " + message(err));
      return false;
    }
    paint(true);
    if (RB.sound) RB.sound.play("move", { flips: tut.view.flipped.length });
    tut.step++;
    $("tut-intro").textContent = "";  // la bienvenida solo se ve antes de la primera jugada
    return true;
  }

  /* Espera a que el jugador pulse el botón («Continuar», o el texto que se pida) o haga clic en el tablero. */
  function continuePressed(token, label) {
    return new Promise((resolve) => {
      const done = () => {
        $("tut-chart").removeEventListener("click", done);
        if (token === tut.token) actions();
        resolve();
      };
      const btn = button(label || "Continuar ▸", done, "btn--gold");
      actions(btn);
      btn.focus({ preventScroll: true });
      $("tut-chart").addEventListener("click", done);
    });
  }

  function finishLesson() {
    const lesson = tut.lessons[tut.index];
    tut.busy = false; tut.allowed = new Set();
    passLesson();
    paint(false);
    say(lesson.done, "fin");
    if (RB.sound) RB.sound.play("win");
    actions(...afterButtons());
  }

  /* Marca la lección como superada: la siguiente queda desbloqueada en la lista. */
  function passLesson() {
    tut.seen = Math.max(tut.seen, tut.index + 1);
    saveSeen();
    renderLessons();
  }

  function afterButtons() {
    const last = tut.index === tut.lessons.length - 1;
    return [
      last ? null : button("Siguiente lección", () => startLesson(tut.index + 1), "btn--gold"),
      button("Repetir la lección", () => startLesson(tut.index), "btn--paper"),
      last ? h("a", { class: "btn btn--sm btn--gold", href: "#/jugar", text: "¡A luchar!" }) : null,
    ];
  }

  // ------------------------------------------------------------- juego libre --- //

  /* Prepara la partida contra el bot de la lección, con una semilla nueva en cada intento. */
  async function startFree(token, lesson) {
    try {
      await RB.engine.call("start_match", [null, lesson.rival, Math.floor(Math.random() * 2 ** 31)]);
    } catch (err) {
      if (token === tut.token) fail("No se pudo preparar al rival: " + message(err));
      return;
    }
    if (token !== tut.token) return;
    say("Te toca. Puedes jugar en cualquier casilla marcada con la brújula.", "tu");
    freeTurn(token);
  }

  /* Un turno de la partida libre: si te toca, el motor valora tus jugadas y esperas; si no, mueve el bot. */
  async function freeTurn(token) {
    const view = tut.view;
    if (view.over) return finishFree();
    if (view.turn === 1) {
      try {
        tut.coach = await RB.engine.call("coach", [view.state]);
      } catch (err) {
        if (token === tut.token) fail("El mentor no pudo valorar las jugadas: " + message(err));
        return;
      }
      if (token !== tut.token) return;
      tut.allowed = new Set(view.legal.map(key)); tut.busy = false;  // cualquier jugada legal
      paint(false);
      return;
    }
    tut.busy = true; tut.allowed = new Set();
    paint(false);
    await wait(RIVAL_DELAY_MS);
    if (token !== tut.token) return;
    let after;
    try {
      after = await RB.engine.call("bot_move", [view.state], { timeout: BOT_TIMEOUT_MS });
    } catch (err) {
      if (token === tut.token) fail("El rival no pudo mover: " + message(err));
      return;
    }
    if (token !== tut.token) return;
    tut.view = after;
    paint(!after.forfeit);
    const said = tut.advice ? tut.advice.text + " " : "";
    if (after.forfeit) {
      say(said + "El rival ha perdido por incumplir las reglas.", "rival");
    } else {
      if (RB.sound) RB.sound.play("move", { flips: after.flipped.length });
      const pass = after.passed ? " No tienes jugadas posibles: pasas, y vuelve a mover el rival." : "";
      say(said + "El rival juega " + after.notation + " y voltea " + fichas(after.flipped.length) + "." + pass, tut.advice ? tut.advice.who : "rival");
    }
    freeTurn(token);
  }

  /* Buena o mala por las fichas que puede quitarte el rival en su respuesta, comparada con la jugada
   * más segura que tenías. Los números los ha calculado el motor (coach) antes de jugar. */
  function advise(move) {
    const options = tut.coach || [];
    const mine = options.find((o) => key(o.move) === key(move));
    if (!mine) return { text: "", who: "tu" };
    const safest = options.reduce((a, b) => (b.risk < a.risk ? b : a), mine);
    const loses = (o) => (o.risk === 0 ? "no puede quitarte ninguna ficha" : "puede quitarte " + fichas(o.risk));
    if (mine.risk <= safest.risk) {
      return { text: "¡Buena jugada! Con " + mine.notation + " el rival " + loses(mine) + ".", who: "bien" };
    }
    return {
      text: "Cuidado: con " + mine.notation + " el rival " + loses(mine) + (mine.reply ? " jugando en " + mine.reply : "")
        + ". Con " + safest.notation + " " + (safest.risk === 0 ? "no habría podido quitarte ninguna." : "solo habrían sido " + safest.risk + "."),
      who: "mal",
    };
  }

  function finishFree() {
    const lesson = tut.lessons[tut.index];
    const view = tut.view;
    tut.busy = false; tut.allowed = new Set();
    paint(false);
    const score = "Calaveras " + view.score[0] + " – " + view.score[1] + " Sombreros.";
    if (view.winner === 1) {
      passLesson();
      say(lesson.win + " " + score, "fin");
      if (RB.sound) RB.sound.play("win");
      actions(...afterButtons());
      return;
    }
    say((view.winner === 0 ? "¡Empate! Casi lo tienes. " : "") + lesson.lose + " " + score, "error");
    if (RB.sound) RB.sound.play("lose");
    actions(button("Reintentar", () => startLesson(tut.index), "btn--gold"));
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

  /* Cada vez que se entra, el tutorial empieza por la lección 1 con la bienvenida. Las lecciones ya
   * superadas siguen marcadas en la lista y desbloqueadas, por si se quiere saltar a ellas. */
  async function enter() {
    if (tut.ready) { startLesson(0); return; }
    if (tut.started) return;  // se están cargando las lecciones o el motor: al terminar empieza la 1
    tut.started = true;
    if (!cells.length) buildBoard();
    say("Cargando las lecciones y el motor de Python…");
    try {
      tut.lessons = await load();
      await whenEngineReady();
    } catch (err) {
      tut.started = false;
      say("No se pudo empezar el tutorial: " + message(err));
      actions(button("Reintentar", () => { if (RB.engine.state === "error") RB.engine.restart(); enter(); }));
      return;
    }
    tut.seen = Math.min(readSeen(), tut.lessons.length);
    tut.ready = true;
    startLesson(0);
  }

  RB.tutorial = { enter: enter };
})();
