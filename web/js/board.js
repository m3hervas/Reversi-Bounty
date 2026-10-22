/* El tablero: una sola función que lo pinta entero a partir de una posición.
 *
 *   RB.paintBoard(container, view, opts)
 *
 * `view` es lo que devuelve el puente de Python (webglue._vista): el tablero, las jugadas
 * legales, el turno… Esta función no sabe nada de reglas: no decide qué casillas son
 * legales ni qué fichas se voltean, solo dibuja lo que le dice el motor.
 *
 * Cada llamada BORRA el tablero anterior y lo construye de nuevo desde `view`. No se
 * parchean casillas sueltas: así lo que se ve no puede desincronizarse del estado.
 *
 * opts:
 *   onPick(move)   si se pasa, las casillas son botones y las jugadas legales de `view` se
 *                  pueden pulsar
 *   locked         true cuando no es tu turno: siguen siendo botones (el foco del teclado no
 *                  se pierde), pero ninguna casilla se puede jugar
 *   human         1 | -1, color de la persona (para la ficha «fantasma» al pasar el ratón)
 *   last           [fila, columna] de la última jugada, que se resalta
 *   flipped        fichas que acaban de voltearse (para animarlas)
 *   animate        true solo justo después de una jugada: la nueva cae y las volteadas giran
 *   hints          true para dibujar un diagrama: marca las jugadas legales de `view` aunque
 *                  el tablero no sea interactivo (las casillas siguen sin ser botones)
 *   marks          casillas que se señalan sobre el tablero. Una lista de [fila, columna] se dibuja
 *                  con el aro de «volteada»; un objeto { tipo: [casillas] } elige el dibujo de cada
 *                  grupo: flip, anchor, target, deny, corner, x, c (ver board.css)
 *   label          nombre accesible del tablero
 *
 * También define RB.h, un ayudante mínimo para crear elementos que usa el resto de la web.
 */
(function () {
  "use strict";

  const RB = (window.RB = window.RB || {});
  const SIZE = 8;
  const COLS = "abcdefgh";
  const FLIP_BASE_MS = 90;  // la primera ficha gira cuando ya ha caído la nueva
  const FLIP_STEP_MS = 55;  // y cada casilla de distancia, un poco más tarde
  const COLOR_WORD = { 1: "ficha negra", "-1": "ficha blanca", 0: "vacía" };
  const EMPTY = Array.from({ length: SIZE }, () => Array(SIZE).fill(0));

  /* h("button", { class: "x", dataset: { r: "1" }, text: "…" }, hijo, …) */
  function h(tag, attrs, ...children) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([key, value]) => {
      if (value === null || value === undefined || value === false) return;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key === "dataset") Object.assign(node.dataset, value);
      else if (key === "style") node.style.cssText = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    });
    children.flat().forEach((child) => {
      if (child !== null && child !== undefined && child !== false) {
        node.append(child instanceof Node ? child : document.createTextNode(String(child)));
      }
    });
    return node;
  }

  /* Solo para etiquetar casillas: el motor da la notación de las jugadas. */
  function cellName(r, c) { return COLS[c] + (r + 1); }
  function key(move) { return move[0] + "," + move[1]; }

  function paintBoard(container, view, opts) {
    opts = opts || {};
    const board = view ? view.state.board : EMPTY;
    const interactive = typeof opts.onPick === "function";
    const playable = new Set(interactive && view && !opts.locked ? view.legal.map(key) : []);
    const last = opts.last ? key(opts.last) : null;
    const animate = !!opts.animate;
    const flipped = new Set(animate ? (opts.flipped || []).map(key) : []);
    const hinted = new Set(!interactive && opts.hints && view ? view.legal.map(key) : []);
    const marked = new Map(); // casilla -> tipo de marca
    if (Array.isArray(opts.marks)) opts.marks.forEach((sq) => marked.set(key(sq), "flip"));
    else Object.entries(opts.marks || {}).forEach(([kind, list]) => list.forEach((sq) => marked.set(key(sq), kind)));

    // El foco del teclado sobrevive al repintado: se recuerda la casilla, no el elemento.
    const hadFocus = container.contains(document.activeElement);
    let focusKey = container.dataset.focus;
    if (!focusKey || (playable.size && !playable.has(focusKey) && !hadFocus)) {
      focusKey = playable.size ? playable.values().next().value : "3,3";
    }

    const grid = h("div", {
      class: "bd__grid",
      role: interactive ? "group" : "img",
      "aria-label": opts.label || "Tablero",
    });
    for (let r = 0; r < SIZE; r++) {
      for (let c = 0; c < SIZE; c++) {
        const k = r + "," + c;
        const color = board[r][c];
        const canPlay = playable.has(k);
        const cell = h(interactive ? "button" : "span", {
          class: "cell",
          type: interactive ? "button" : null,
          tabindex: interactive ? (k === focusKey ? "0" : "-1") : null,
          dataset: { r: String(r), c: String(c) },
          "aria-label": interactive
            ? cellName(r, c) + ", " + COLOR_WORD[color] + (canPlay ? ", jugada posible" : "") + (k === last ? ", última jugada" : "")
            : null,
          "aria-disabled": interactive && !canPlay ? "true" : null,
        });
        if (canPlay) cell.dataset.playable = "";
        if (hinted.has(k)) cell.dataset.hint = "";
        if (marked.has(k)) cell.dataset.mark = marked.get(k);
        if (k === last) cell.dataset.last = "";
        if (color !== 0) {
          const disc = h("span", { class: "disc", dataset: { color: String(color) } });
          if (animate && k === last) {
            disc.dataset.anim = "place";
          } else if (flipped.has(k)) {
            // Una ficha recién creada no puede girar desde el color viejo, así que se
            // dibujan dos: la vieja se estrecha hasta desaparecer y la nueva se ensancha.
            const dist = opts.last ? Math.max(Math.abs(opts.last[0] - r), Math.abs(opts.last[1] - c)) : 1;
            const delay = "--delay:" + (FLIP_BASE_MS + (dist - 1) * FLIP_STEP_MS) + "ms";
            disc.dataset.anim = "flip";
            disc.style.cssText = delay;
            cell.append(h("span", { class: "disc disc--old", dataset: { color: String(-color) }, style: delay, "aria-hidden": "true" }));
          }
          cell.append(disc);
        }
        grid.append(cell);
      }
    }

    if (interactive) {
      grid.addEventListener("click", (event) => {
        const cell = event.target.closest(".cell");
        if (cell && cell.dataset.playable !== undefined) opts.onPick([Number(cell.dataset.r), Number(cell.dataset.c)]);
      });
      grid.addEventListener("keydown", (event) => moveFocus(grid, event));
      grid.addEventListener("focusin", (event) => {
        const cell = event.target.closest(".cell");
        if (cell) container.dataset.focus = cell.dataset.r + "," + cell.dataset.c;
      });
    }

    const root = h("div", {
      class: "bd",
      dataset: { human: opts.human ? String(opts.human) : "", turn: playable.size ? "human" : "wait" },
    },
      h("div", { class: "bd__cols", "aria-hidden": "true" }, Array.from(COLS, (ch) => h("span", { text: ch }))),
      h("div", { class: "bd__rows", "aria-hidden": "true" }, Array.from({ length: SIZE }, (_, i) => h("span", { text: String(i + 1) }))),
      h("div", { class: "bd__frame" }, grid),
    );
    container.replaceChildren(root);
    container.dataset.focus = focusKey;
    if (interactive && hadFocus) {
      const target = grid.querySelector('[tabindex="0"]');
      if (target) target.focus({ preventScroll: true });
    }
  }

  /* Flechas para moverse por el tablero (Intro o espacio pulsan la casilla: son botones). */
  function moveFocus(grid, event) {
    const steps = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
    const step = steps[event.key];
    const cell = event.target.closest(".cell");
    if (!step || !cell) return;
    event.preventDefault();
    const r = Math.min(SIZE - 1, Math.max(0, Number(cell.dataset.r) + step[0]));
    const c = Math.min(SIZE - 1, Math.max(0, Number(cell.dataset.c) + step[1]));
    const next = grid.children[r * SIZE + c];
    cell.tabIndex = -1;
    next.tabIndex = 0;
    next.focus();
  }

  RB.h = h;
  RB.paintBoard = paintBoard;
})();
