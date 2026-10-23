/* La partida: una persona contra un bot del registro.
 *
 * Este archivo solo orquesta. Cada pregunta sobre el juego (qué jugadas hay, qué pasa al
 * jugar, quién gana, qué juega el bot) se la hace al motor de Python a través de
 * RB.engine, y cada respuesta se dibuja entera con RB.paintBoard.
 *
 * Cómo sobrevive a quien la usa:
 *   - `busy`: mientras se espera a Python no se acepta ningún clic (doble clic, clics
 *     durante el turno del bot o después del final no hacen nada).
 *   - `token`: cada partida nueva lo sube. Una respuesta que llega de una partida ya
 *     abandonada se descarta en lugar de pintarse encima de la nueva.
 *   - La partida se guarda en localStorage tras cada jugada: si se recarga la página, se
 *     vuelve a crear el bot con la misma semilla y se sigue desde la posición guardada.
 *   - Si el bot falla, pierde y se cuenta por qué; si no contesta a tiempo, se reinicia el
 *     motor y también pierde. Ningún fallo deja la página en blanco o un botón muerto.
 */
(function () {
  "use strict";

  const RB = window.RB;
  const h = RB.h;
  const STORE_GAME = "rb-partida";
  const STORE_PREFS = "rb-ajustes";
  const BOT_DELAY_MS = 600;     // pausa antes de que mueva el bot: así se ve la jugada
  const PASS_DELAY_MS = 1300;   // tiempo para leer el aviso de paso
  const BOT_TIMEOUT_MS = 20000; // un bot que tarda más se da por colgado
  const COLOR = { 1: "negras", "-1": "blancas" };

  const game = {
    token: 0,
    phase: "setup",  // setup | playing | over
    players: [],
    bot: null,       // identidad del rival: { name, icon, authors, description }
    human: 1,        // color de la persona
    seed: 0,
    view: null,      // la última respuesta del motor
    busy: false,
  };
  const ui = {};

  // ------------------------------------------------------------- utilidades --- //

  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const message = (err) => (err && err.message ? err.message : String(err));

  function store(key, value) {
    try {
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, JSON.stringify(value));
    } catch (e) { /* sin almacenamiento (modo privado): la web funciona igual */ }
  }

  function load(key) {
    try { return JSON.parse(localStorage.getItem(key) || "null"); } catch (e) { return null; }
  }

  /* El escenario (el avatar del rival) es teatro: si falta o falla, la partida sigue igual. */
  function act(name, ...args) {
    try { return RB.stage && RB.stage[name] ? RB.stage[name](...args) : undefined; } catch (err) { return undefined; }
  }

  /* Un efecto de sonido. Si el sonido no está o está apagado, no hace nada. */
  function cue(kind, extra) {
    if (RB.sound) RB.sound.play(kind, extra);
  }

  function setStatus(state, text) {
    ui.status.dataset.state = state;
    ui.statusText.textContent = text;
  }

  let toastTimer = null;
  function toast(text) {
    clearTimeout(toastTimer);
    ui.toast.textContent = text;
    ui.toast.hidden = false;
    toastTimer = setTimeout(() => { ui.toast.hidden = true; }, PASS_DELAY_MS + 900);
  }

  // ------------------------------------------------------------------ pintar --- //

  /* Dibuja todo lo que depende de la partida a partir de game.view. */
  function render(animate) {
    const view = game.view;
    const humanTurn = game.phase === "playing" && !!view && view.turn === game.human;
    RB.paintBoard(ui.board, view, {
      onPick: onPick,
      locked: !humanTurn,
      human: game.human,
      last: view && view.move,
      flipped: view && view.flipped,
      animate: animate,
      label: "Tablero de la partida",
    });

    // Antes de empezar, los marcadores enseñan lo que está elegido en el formulario.
    const seat = game.phase === "setup" ? selection() : game;
    const score = view ? view.score : [2, 2];
    [1, -1].forEach((color, i) => {
      const plate = document.getElementById("plate-" + color);
      const isHuman = color === seat.human;
      const who = document.getElementById("who-" + color);
      who.textContent = isHuman ? "Tú" : (seat.bot ? seat.bot.name : "Bot");
      who.title = who.textContent; // la placa recorta con «…»: el nombre completo está aquí
      document.getElementById("avatar-" + color).textContent = isHuman ? "🙂" : (seat.bot ? seat.bot.icon : "🤖");
      document.getElementById("count-" + color).textContent = String(score[i]);
      plate.dataset.role = isHuman ? "you" : "rival";
      plate.dataset.turn = String(!!view && game.phase === "playing" && view.turn === color);
      plate.toggleAttribute("data-thinking", game.phase === "playing" && game.busy && !isHuman && !!view && view.turn === color);
    });
    ui.play.dataset.phase = game.phase;
    if (!ui.start.disabled) ui.start.textContent = game.phase === "playing" ? "Nueva partida" : "Empezar partida";
  }

  function showResult() {
    const view = game.view;
    const [black, white] = view.score;
    const mine = game.human === 1 ? black : white;
    const theirs = game.human === 1 ? white : black;
    ui.resultTitle.textContent = view.winner === 0 ? "Empate" : view.winner === game.human ? "Has ganado" : "Gana " + game.bot.name;
    ui.resultScore.textContent = "Tú " + mine + " – " + theirs + " " + game.bot.name;
    ui.resultReason.hidden = !view.forfeit;
    ui.resultReason.textContent = view.forfeit ? "El bot ha perdido por incumplir las reglas: " + view.forfeit + "." : "";
    ui.result.hidden = false;
    ui.rematch.focus({ preventScroll: true });
  }

  // ---------------------------------------------------------------- partida --- //

  function selection() {
    const data = new FormData(ui.form);
    const bot = game.players.find((p) => p.name === data.get("rival")) || game.players[0];
    return { bot: bot, human: Number(data.get("color")) === -1 ? -1 : 1 };
  }

  async function newGame() {
    if (!game.players.length) return;
    const token = ++game.token;
    const choice = selection();
    Object.assign(game, {
      phase: "playing", bot: choice.bot, human: choice.human, busy: true,
      seed: Math.floor(Math.random() * 2 ** 31),
    });
    ui.result.hidden = true;
    ui.toast.hidden = true;
    ui.note.hidden = true;
    ui.rival.textContent = game.bot.name;
    act("reset");
    act("hello");
    setStatus("loading", "Preparando la partida…");
    try {
      await RB.engine.call("start_game", [game.bot.name, -game.human, game.seed]);
      const view = await RB.engine.call("new_game");
      if (token !== game.token) return;
      game.view = view;
    } catch (err) {
      if (token === game.token) failed("No se pudo empezar la partida: " + message(err));
      return;
    }
    save();
    render(false);
    continueGame(token);
  }

  /* Decide qué pasa después de pintar una posición: el final, tu turno o el del bot. */
  function continueGame(token) {
    const view = game.view;
    if (view.over) return finish();
    if (view.turn === game.human) {
      if (view.passed && view.mover === game.human) {
        cue("pass");
        act("passed", "bot");
        toast(game.bot.name + " no tiene jugada y pasa. Te vuelve a tocar.");
      }
      game.busy = false;
      render(false);
      setStatus("you", "Te toca. Elige una de las casillas marcadas.");
    } else {
      botTurn(token);
    }
  }

  function onPick(move) {
    if (game.busy || game.phase !== "playing" || game.view.turn !== game.human) return;
    const token = game.token;
    game.busy = true;
    RB.engine.call("play_move", [game.view.state, move]).then((view) => {
      if (token !== game.token) return;
      game.view = view;
      save();
      render(true);
      cue("move", { flips: view.flipped.length });
      act("humanMoved", view.flipped.length, view.move);
      continueGame(token);
    }, (err) => {
      if (token !== game.token) return;
      game.busy = false;
      render(false);
      setStatus("error", "No se pudo hacer la jugada: " + message(err));
    });
  }

  async function botTurn(token) {
    game.busy = true;
    render(false);
    setStatus("thinking", game.bot.name + " está pensando…");
    act("think", true);
    await wait(BOT_DELAY_MS);
    if (token !== game.token) return;
    let view;
    try {
      view = await RB.engine.call("bot_move", [game.view.state], { timeout: BOT_TIMEOUT_MS });
    } catch (err) {
      if (token !== game.token) return;
      act("think", false);
      if (err.code === "timeout") {
        // El worker se ha reiniciado: el bot pierde, como si hubiera fallado.
        game.view = Object.assign({}, game.view, {
          over: true, turn: null, legal: [], winner: game.human, move: null, flipped: [],
          forfeit: game.bot.name + " no respondió en " + BOT_TIMEOUT_MS / 1000 + " s",
        });
        return finish();
      }
      return failed("El motor no pudo mover al bot: " + message(err));
    }
    if (token !== game.token) return;
    act("think", false);
    if (!view.forfeit) await act("reach", view.move, -game.human); // el brazo lleva la ficha y, al llegar, se pinta
    if (token !== game.token) return;
    game.view = view;
    save();
    render(!view.forfeit);
    if (!view.forfeit) {
      cue("move", { flips: view.flipped.length });
      act("botMoved", view.flipped.length);
    }
    if (!view.over && view.turn !== game.human) {
      // La persona no tiene jugada: pasa y el bot vuelve a mover.
      cue("pass");
      act("passed", "human");
      toast("No tienes jugadas posibles: pasas.");
      setStatus("thinking", "Pasas. " + game.bot.name + " vuelve a mover…");
      await wait(PASS_DELAY_MS);
      if (token !== game.token) return;
    }
    continueGame(token);
  }

  function finish() {
    game.phase = "over";
    game.busy = false;
    store(STORE_GAME, null);
    render(false);
    const view = game.view;
    setStatus("over", view.forfeit
      ? game.bot.name + " ha perdido por incumplir las reglas."
      : "Fin de la partida. " + (view.winner === 0 ? "Empate." : view.winner === game.human ? "Has ganado." : "Gana " + game.bot.name + "."));
    showResult();
    cue(view.forfeit || view.winner === game.human ? "win" : view.winner === 0 ? "draw" : "lose");
    if (view.forfeit) act("forfeit");
    else act("finish", view.winner === 0 ? "draw" : view.winner === game.human ? "human" : "bot");
  }

  /* Un error que no es culpa del bot (el motor, la red…): se cuenta y se puede seguir. */
  function failed(text) {
    game.phase = "over";
    game.busy = false;
    store(STORE_GAME, null);
    render(false);
    setStatus("error", text + " Pulsa «Empezar partida» para intentarlo de nuevo.");
  }

  // ----------------------------------------------------- guardar y recuperar --- //

  function save() {
    if (game.phase !== "playing" || !game.view || game.view.over) return store(STORE_GAME, null);
    store(STORE_GAME, { v: 1, bot: game.bot.name, human: game.human, seed: game.seed, state: game.view.state, last: game.view.move || null });
  }

  /* Sigue la partida guardada antes de recargar. Si algo no cuadra, se olvida sin más. */
  async function resume() {
    const saved = load(STORE_GAME);
    const bot = saved && saved.v === 1 && game.players.find((p) => p.name === saved.bot);
    if (!bot) { store(STORE_GAME, null); return false; }
    const token = ++game.token;
    Object.assign(game, { phase: "playing", bot: bot, human: saved.human === -1 ? -1 : 1, seed: saved.seed, busy: true });
    try {
      await RB.engine.call("start_game", [bot.name, -game.human, saved.seed]);
      const view = await RB.engine.call("view", [saved.state]);
      if (token !== game.token) return true;
      if (view.over) throw new Error("la partida guardada ya había terminado");
      game.view = Object.assign(view, { move: saved.last });
    } catch (err) {
      store(STORE_GAME, null);
      Object.assign(game, { phase: "setup", bot: null, busy: false, view: null });
      return false;
    }
    syncForm();
    ui.rival.textContent = bot.name;
    render(false);
    toast("Hemos recuperado tu partida.");
    continueGame(token);
    return true;
  }

  // ------------------------------------------------------------ preparación --- //

  function renderRivals(players, selected) {
    ui.rivals.replaceChildren(...players.map((p) => h("label", { class: "rival", title: p.name + " · " + p.authors.join(", ") },
      h("input", { type: "radio", name: "rival", value: p.name, checked: p.name === selected }),
      h("span", { class: "rival__icon", "aria-hidden": "true", text: p.icon }),
      h("span", { class: "rival__name" }, h("b", { text: p.name }), h("small", { text: p.authors.join(", ") })),
    )));
    describeRival();
  }

  function describeRival() {
    const choice = selection();
    ui.desc.textContent = choice.bot ? choice.bot.description : "";
    if (game.phase !== "playing") ui.rival.textContent = choice.bot ? choice.bot.name : "un bot";
  }

  function syncForm() {
    const rival = ui.form.querySelector('input[name="rival"][value="' + CSS.escape(game.bot.name) + '"]');
    if (rival) rival.checked = true;
    ui.form.querySelector('input[name="color"][value="' + game.human + '"]').checked = true;
    describeRival();
  }

  function onFormChange() {
    describeRival();
    if (game.phase === "setup") render(false);
    const choice = selection();
    store(STORE_PREFS, { bot: choice.bot && choice.bot.name, human: choice.human });
    ui.note.hidden = game.phase !== "playing" || (choice.bot === game.bot && choice.human === game.human);
  }

  async function onReady(info) {
    game.players = info.players;
    ui.retry.hidden = true;
    if (!game.players.length) {
      ui.rivals.replaceChildren(h("p", { class: "setup__hint", text: "El registro no tiene ningún jugador." }));
      setStatus("error", "No hay rivales: añade un bot a players/.");
      return;
    }
    const prefs = load(STORE_PREFS) || {};
    const known = game.players.some((p) => p.name === prefs.bot);
    renderRivals(game.players, known ? prefs.bot : game.players[0].name);
    if (prefs.human === -1) ui.form.querySelector('input[name="color"][value="-1"]').checked = true;
    ui.start.disabled = false;
    render(false);
    if (game.phase === "playing") return; // el motor se reinició a mitad de partida
    if (await resume()) return;
    if (game.phase !== "setup") return;
    game.view = await RB.engine.call("new_game").catch(() => null);
    render(false);
    setStatus("idle", "Elige rival y color, y pulsa «Empezar partida».");
    act("hello");
  }

  function onFatal(error) {
    ui.start.disabled = true;
    ui.start.textContent = "Motor no disponible";
    ui.rivals.replaceChildren(h("p", { class: "setup__hint", text: "No se han podido cargar los jugadores." }));
    setStatus("error", "No se pudo arrancar el motor de Python: " + error);
    ui.retry.hidden = false;
  }

  function init() {
    ["play", "board", "toast", "status", "rivals", "result", "rematch", "change", "retry", "start"].forEach((id) => {
      ui[id] = document.getElementById(id);
    });
    Object.assign(ui, {
      form: document.getElementById("setup"),
      statusText: document.getElementById("status-text"),
      desc: document.getElementById("rival-desc"),
      note: document.getElementById("setup-note"),
      rival: document.getElementById("play-rival"),
      resultTitle: document.getElementById("result-title"),
      resultScore: document.getElementById("result-score"),
      resultReason: document.getElementById("result-reason"),
    });

    act("init");
    render(false);
    // Antes de que Python arranque, el tablero ya enseña la posición de salida (precalculada).
    RB.portada.then((data) => {
      if (data && !game.view && game.phase === "setup") {
        game.view = data.inicio;
        render(false);
      }
    });
    ui.form.addEventListener("submit", (event) => { event.preventDefault(); newGame(); });
    ui.form.addEventListener("change", onFormChange);
    ui.rematch.addEventListener("click", newGame);
    ui.change.addEventListener("click", () => {
      ui.result.hidden = true;
      game.phase = "setup";
      render(false);
      setStatus("idle", "Elige rival y color, y pulsa «Empezar partida».");
      const checked = ui.form.querySelector('input[name="rival"]:checked');
      if (checked) checked.focus();
    });
    ui.retry.addEventListener("click", () => {
      ui.retry.hidden = true;
      setStatus("loading", "Reintentando…");
      RB.engine.restart();
    });

    RB.engine.on("status", (text) => { if (game.phase === "setup" && !game.players.length) setStatus("loading", text); });
    RB.engine.on("ready", (info) => { onReady(info).catch(RB.reportError); });
    RB.engine.on("fatal", onFatal);
  }

  RB.views = RB.views || {};
  /* Deja elegido un rival en el formulario (lo usa la página de Bots). Solo cambia lo que se
   * verá en la próxima partida: no toca una partida en curso. */
  function selectRival(name) {
    const radio = ui.form && ui.form.querySelector('input[name="rival"][value="' + CSS.escape(name) + '"]');
    if (!radio) return false;
    radio.checked = true;
    onFormChange();
    return true;
  }

  /* «Jugar contra X» desde la página de Bots: si no hay una partida en curso, empieza una contra
   * ese bot; si la hay, no la pisa (solo deja el rival elegido para la próxima). */
  function playAgainst(name) {
    if (!selectRival(name)) return false;
    if (game.phase !== "playing" && !ui.start.disabled) newGame();
    return true;
  }

  RB.views.jugar = {
    init: init,
    selectRival: selectRival,
    playAgainst: playAgainst,
    enter() {
      // Al volver a este apartado, el foco vuelve al tablero si es tu turno.
      if (game.phase === "playing" && !game.busy) render(false);
    },
  };
})();
