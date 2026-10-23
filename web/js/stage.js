/* El escenario de la partida: el avatar del rival, su bocadillo y su brazo.
 *
 * Esto es solo teatro. No decide nada del juego: play.js le cuenta lo que pasa («has jugado»,
 * «mueve el bot», «pasa», «fin») y el escenario hace reaccionar al personaje. Si algo aquí falla,
 * la partida sigue igual: todas las llamadas son opcionales y a prueba de errores.
 *
 *   RB.stage.init()                   engancha el escenario con el HTML (lo llama play.js)
 *   RB.stage.setAvatar(avatar)        cambia el personaje (ver avatars.js)
 *   RB.stage.hello()                  saluda al empezar
 *   RB.stage.think(true|false)        «pensando…» mientras el bot decide
 *   RB.stage.reach(move, color)       el brazo lleva la ficha a la casilla; promesa que se cumple
 *                                     cuando llega (entonces se pinta la ficha en el tablero)
 *   RB.stage.humanMoved(flips)        reacciona a la jugada de la persona
 *   RB.stage.botMoved(flips)          reacciona a la jugada del bot
 *   RB.stage.passed(quien)            "bot" o "human": alguien pasa
 *   RB.stage.finish(result)           "human" (gana la persona), "bot" o "draw"
 *   RB.stage.reset()                  deja al personaje en calma
 *
 * Decisiones de movimiento:
 *   - El brazo se anima con la API Web Animations y solo con transform (la GPU lo compone sin
 *     recalcular el diseño): 300 ms al estirarse, con salida rápida, y 240 ms al recogerse. Pasa
 *     decenas de veces por partida, así que tiene que ser ágil.
 *   - Los bucles tranquilos (respirar, parpadear, mecerse) son CSS en avatar.css.
 *   - Con «reducir movimiento» el brazo no se estira: la ficha aparece y el personaje solo cambia
 *     de cara.
 */
(function () {
  "use strict";

  const RB = window.RB;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const canHover = window.matchMedia("(hover: hover) and (pointer: fine)");
  const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)";
  const EASE_IN_OUT = "cubic-bezier(0.77, 0, 0.175, 1)";
  const REACH_MS = 300;
  const RETRACT_MS = 240;
  const BIG_FLIPS = 4;        // desde cuántas fichas volteadas una jugada es «grande»
  const BUBBLE_MS = 2600;
  const VIEWBOX = [400, 480]; // el viewBox de todos los dibujos de avatar

  const ui = {};
  const state = { avatar: null, base: "neutral", moodTimer: null, bubbleTimer: null, flight: null, lookQueued: false };

  const pick = (list) => list[Math.floor(Math.random() * list.length)];

  // ------------------------------------------------------------ el dibujo --- //

  function mount(avatar) {
    const doc = new DOMParser().parseFromString(avatar.svg, "image/svg+xml");
    const svg = document.importNode(doc.documentElement, true);
    ui.avatarHost.replaceChildren(svg);
    ui.svg = svg;
    ui.irises = Array.from(svg.querySelectorAll(".av__iris"));
    ui.stage.style.setProperty("--spot", avatar.spot);
    ui.stage.dataset.avatar = avatar.id;
  }

  /* Un punto del dibujo (en su viewBox) convertido a coordenadas de la pantalla. */
  function screenPoint(point) {
    const rect = ui.svg.getBoundingClientRect();
    return [rect.left + (point[0] / VIEWBOX[0]) * rect.width, rect.top + (point[1] / VIEWBOX[1]) * rect.height];
  }

  // -------------------------------------------------------------- ánimo --- //

  function setMood(mood, ms) {
    if (!ui.svg) return;
    clearTimeout(state.moodTimer);
    ui.svg.dataset.mood = mood;
    if (ms) state.moodTimer = setTimeout(() => { ui.svg.dataset.mood = state.base; }, ms);
  }

  /* Un gesto de una sola vez (un saltito con el pelo). Se reinicia aunque se repita enseguida. */
  function flourish() {
    if (!ui.svg) return;
    ui.svg.classList.remove("is-flourish");
    void ui.svg.getBoundingClientRect(); // fuerza a reiniciar la animación
    ui.svg.classList.add("is-flourish");
  }

  function say(key, ms) {
    const lines = state.avatar && state.avatar.lines[key];
    if (!lines || !ui.bubble) return;
    clearTimeout(state.bubbleTimer);
    ui.bubbleText.textContent = pick(lines);
    ui.bubble.dataset.kind = key;
    ui.bubble.classList.add("is-on");
    const lifetime = ms === undefined ? BUBBLE_MS : ms;
    if (lifetime) state.bubbleTimer = setTimeout(hideBubble, lifetime);
  }

  function hideBubble() {
    clearTimeout(state.bubbleTimer);
    if (ui.bubble) ui.bubble.classList.remove("is-on");
  }

  // ------------------------------------------------------- los ojos miran --- //

  /* Las pupilas siguen al puntero mientras está sobre el escenario. Se pone el transform
   * directamente en cada pupila (son dos) y solo con ratón: en el móvil no hay puntero. */
  function lookAt(x, y) {
    if (!ui.svg || state.lookQueued) return;
    state.lookQueued = true;
    requestAnimationFrame(() => {
      state.lookQueued = false;
      const head = screenPoint(state.avatar.head);
      const dx = x - head[0];
      const dy = y - head[1];
      const distance = Math.hypot(dx, dy) || 1;
      const strength = Math.min(1, distance / 280);
      const px = (dx / distance) * 6.5 * strength;
      const py = (dy / distance) * 4.5 * strength;
      ui.irises.forEach((iris) => { iris.style.transform = "translate(" + px.toFixed(2) + "px, " + py.toFixed(2) + "px)"; });
    });
  }

  function lookAtCell(move) {
    const cell = cellFor(move);
    if (!cell) return;
    const rect = cell.getBoundingClientRect();
    lookAt(rect.left + rect.width / 2, rect.top + rect.height / 2);
  }

  function cellFor(move) {
    return ui.board.querySelector('.cell[data-r="' + move[0] + '"][data-c="' + move[1] + '"]');
  }

  // ------------------------------------------------------- el brazo estirado --- //

  function hideReach() {
    ui.reach.hidden = true;
    if (ui.svg) ui.svg.classList.remove("is-reach");
    ui.reachDisc.style.opacity = "";
  }

  /* Corta cualquier brazo a medias (una partida nueva no debe heredar un brazo en el aire). */
  function cancelReach() {
    if (state.flight) state.flight.forEach((animation) => animation.cancel());
    state.flight = null;
    hideReach();
  }

  /* El brazo sale del hombro, se estira hasta la casilla y suelta la ficha. Se dibuja como una barra
   * girada hacia el destino y estirada con scaleX; la mano viaja por el mismo camino con translateX,
   * a la misma vez y con la misma curva, así que siempre quedan pegadas. */
  function reach(move, color) {
    if (!state.avatar || reduceMotion.matches || !move) return Promise.resolve();
    const cell = cellFor(move);
    if (!cell) return Promise.resolve();
    cancelReach();

    const stage = ui.stage.getBoundingClientRect();
    const from = screenPoint(state.avatar.shoulder);
    const rect = cell.getBoundingClientRect();
    const to = [rect.left + rect.width / 2, rect.top + rect.height / 2];
    const dx = to[0] - from[0];
    const dy = to[1] - from[1];
    const length = Math.hypot(dx, dy);
    const start = 0.16; // el brazo arranca un poco estirado, no desde cero

    ui.reach.style.left = from[0] - stage.left + "px";
    ui.reach.style.top = from[1] - stage.top + "px";
    ui.reach.style.transform = "rotate(" + Math.atan2(dy, dx) + "rad)";
    ui.arm.style.width = length + "px";
    ui.reachDisc.dataset.color = String(color);
    ui.reachDisc.style.opacity = "1";
    ui.reach.hidden = false;
    ui.svg.classList.add("is-reach");

    const timing = { duration: REACH_MS, easing: EASE_OUT, fill: "forwards" };
    const out = [
      ui.arm.animate([{ transform: "scaleX(" + start + ")" }, { transform: "scaleX(1)" }], timing),
      ui.hand.animate([{ transform: "translateX(" + length * start + "px)" }, { transform: "translateX(" + length + "px)" }], timing),
    ];
    state.flight = out;

    return out[1].finished.then(() => {
      if (state.flight !== out) return; // llegó una partida nueva: ya no hay nada que recoger
      ui.reachDisc.style.opacity = "0"; // la ficha ya la pinta el tablero
      const back = { duration: RETRACT_MS, easing: EASE_IN_OUT, fill: "forwards" };
      const retract = [
        ui.arm.animate([{ transform: "scaleX(1)" }, { transform: "scaleX(" + start + ")" }], back),
        ui.hand.animate([{ transform: "translateX(" + length + "px)" }, { transform: "translateX(" + length * start + "px)" }], back),
      ];
      state.flight = retract;
      retract[1].finished.then(() => { if (state.flight === retract) { state.flight = null; hideReach(); } }, () => {});
    }, () => {});
  }

  // --------------------------------------------------------- lo que pasa --- //

  const stage = {
    init() {
      if (ui.stage) return;
      ["stage", "avatar", "bubble", "bubble-text", "board", "reach"].forEach((id) => {
        ui[id.replace(/-(\w)/g, (_, c) => c.toUpperCase())] = document.getElementById(id);
      });
      if (!ui.stage || !RB.avatars) return;
      ui.avatarHost = ui.avatar;
      ui.arm = ui.reach.querySelector(".reach__arm");
      ui.hand = ui.reach.querySelector(".reach__hand");
      ui.reachDisc = ui.reach.querySelector(".reach__disc");
      stage.setAvatar(RB.avatars.forBot());
      if (canHover.matches) {
        ui.stage.addEventListener("pointermove", (event) => lookAt(event.clientX, event.clientY), { passive: true });
        ui.stage.addEventListener("pointerleave", () => ui.irises.forEach((iris) => { iris.style.transform = ""; }));
      }
    },

    setAvatar(avatar) {
      if (!avatar) return;
      state.avatar = avatar;
      mount(avatar);
      const name = document.getElementById("avatar-name");
      if (name) name.textContent = avatar.name;
    },

    hello() { cancelReach(); state.base = "neutral"; setMood("neutral"); flourish(); say("hello"); },

    think(on) {
      state.base = on ? "think" : "neutral";
      setMood(state.base);
      if (on) say("think", 0);
      else hideBubble();
    },

    reach: reach,

    humanMoved(flips, move) {
      if (move) lookAtCell(move);
      if (flips >= BIG_FLIPS) {
        setMood("surprised", 1500);
        say("yourBigMove");
      } else {
        hideBubble();
      }
    },

    botMoved(flips) {
      flourish();
      if (flips >= BIG_FLIPS) {
        setMood("happy", 1700);
        say("bigMove");
      } else {
        say("move", 1600);
      }
    },

    passed(who) {
      setMood(who === "bot" ? "neutral" : "happy", 1600);
      say(who === "bot" ? "pass" : "youPass", 2200);
    },

    finish(result) {
      cancelReach();
      state.base = result === "bot" ? "happy" : result === "human" ? "sad" : "neutral";
      setMood(state.base);
      ui.svg.classList.toggle("is-win", result === "bot");
      say(result === "bot" ? "win" : result === "human" ? "lose" : "draw", 0);
    },

    forfeit() { cancelReach(); state.base = "sad"; setMood("sad"); say("forfeit", 0); },

    reset() {
      cancelReach();
      state.base = "neutral";
      if (ui.svg) { ui.svg.classList.remove("is-win"); setMood("neutral"); }
      hideBubble();
    },
  };

  RB.stage = stage;
})();
