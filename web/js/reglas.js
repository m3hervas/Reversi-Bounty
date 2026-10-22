/* La página de Reglas: los diagramas los dibuja el motor de Python.
 *
 * El texto de la página es HTML normal (se lee sin JavaScript y lo encuentran los buscadores),
 * pero ningún tablero se dibuja a mano: cada <figure data-diagram="nombre"> se rellena
 * reproduciendo con el motor las jugadas de data/reglas.json. Así los diagramas no pueden
 * desfasarse del juego, y tests/test_web_reglas.py comprueba con el mismo motor que lo que
 * dice cada pie de figura es verdad.
 *
 * Mientras Python arranca, cada figura enseña un tablero vacío; si el motor falla, un aviso.
 */
(function () {
  "use strict";

  const RB = window.RB;
  const DATA_URL = "data/reglas.json?v=1";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  /* Cada grupo de «marcas» del JSON se dibuja con un tipo de marca de board.css. */
  const MARK_KINDS = { volteables: "flip", anclas: "anchor", destino: "target", prohibidas: "deny", esquinas: "corner", x: "x", c: "c" };
  let data = null;
  let drawn = false;

  // --------------------------------------------------------------- diagramas --- //

  /* La posición de un diagrama: se parte de la inicial y se juega cada jugada con el motor. */
  async function position(diagram) {
    let view = await RB.engine.call("new_game");
    for (const move of diagram.jugadas) view = await RB.engine.call("play_move", [view.state, move]);
    return view;
  }

  /* «d3» -> [2, 3]. Es solo notación (letra = columna, número = fila), no una regla del juego. */
  function square(name) {
    return [Number(name.slice(1)) - 1, "abcdefgh".indexOf(name[0])];
  }

  /* Las marcas de un diagrama. Las fichas volteadas las da el motor (view.flipped), no el JSON. */
  function marksFor(diagram, view) {
    const marks = {};
    Object.entries(diagram.marcas || {}).forEach(([group, squares]) => {
      if (MARK_KINDS[group]) marks[MARK_KINDS[group]] = squares.map(square);
    });
    if (diagram.volteadas) marks.flip = view.flipped;
    return marks;
  }

  function figures() {
    return Array.from(document.querySelectorAll("figure[data-diagram]"));
  }

  function showPlaceholders() {
    figures().forEach((figure) => {
      const host = figure.querySelector(".figure__board");
      host.dataset.state = "loading";
      RB.paintBoard(host, null, { label: "Tablero cargándose" });
    });
  }

  function showFailure(text) {
    figures().forEach((figure) => {
      const host = figure.querySelector(".figure__board");
      host.dataset.state = "error";
      host.replaceChildren(RB.h("p", { class: "figure__error", role: "status", text: text }));
    });
  }

  async function drawAll() {
    if (drawn) return;
    drawn = true;
    try {
      if (!data) {
        const response = await fetch(DATA_URL);
        if (!response.ok) throw new Error("no se encontró data/reglas.json (HTTP " + response.status + ")");
        data = await response.json();
      }
      for (const figure of figures()) {
        const diagram = data.diagramas[figure.dataset.diagram];
        const host = figure.querySelector(".figure__board");
        if (!diagram) throw new Error("falta el diagrama «" + figure.dataset.diagram + "»");
        const view = await position(diagram);
        RB.paintBoard(host, view, {
          hints: diagram.pistas,
          last: diagram.ultima ? view.move : null,
          marks: marksFor(diagram, view),
          label: diagram.etiqueta,
        });
        host.dataset.state = "ready";
      }
    } catch (err) {
      drawn = false; // se podrá reintentar la próxima vez que arranque el motor
      showFailure("No se pudieron dibujar los diagramas: " + (err && err.message ? err.message : err));
    }
  }

  // ------------------------------------------------------ índice de la página --- //

  /* Los botones del índice llevan a una sección sin tocar la dirección (que ya la usan las rutas),
   * y el índice marca la sección que se está leyendo: la última cuyo borde superior ya ha pasado
   * del tercio superior de la pantalla. Con secciones anidadas (una regla dentro de «Las cuatro
   * reglas») gana la más profunda, porque va después en el documento. */
  function initToc() {
    const buttons = Array.from(document.querySelectorAll(".toc button"));
    const targets = buttons.map((button) => document.getElementById(button.dataset.scroll));
    const sectionsInOrder = buttons
      .map((button, i) => ({ button: button, target: targets[i] }))
      .filter((item) => item.target)
      .sort((a, b) => (a.target.compareDocumentPosition(b.target) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));

    buttons.forEach((button, i) => {
      button.addEventListener("click", () => {
        if (targets[i]) targets[i].scrollIntoView({ behavior: reduceMotion.matches ? "auto" : "smooth", block: "start" });
      });
    });

    let queued = false;
    function mark() {
      queued = false;
      if (document.documentElement.dataset.view !== "reglas") return;
      const line = window.innerHeight * 0.33;
      let active = null;
      sectionsInOrder.forEach((item) => { if (item.target.getBoundingClientRect().top <= line) active = item.button; });
      buttons.forEach((button) => button.toggleAttribute("aria-current", button === active));
      // En pantallas estrechas el índice es una fila que se desliza: se mantiene a la vista el activo.
      if (active && active.scrollIntoView && window.matchMedia("(max-width: 1039px)").matches) {
        const row = active.closest("ol");
        if (row) row.scrollTo({ left: active.offsetLeft - 24, behavior: reduceMotion.matches ? "auto" : "smooth" });
      }
    }
    window.addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(mark); } }, { passive: true });
    mark();
  }

  function init() {
    showPlaceholders();
    initToc();
    RB.engine.on("ready", () => { drawAll(); });
    RB.engine.on("fatal", (error) => showFailure("El motor de Python no arrancó: " + error));
    RB.engine.on("restart", () => { drawn = false; showPlaceholders(); });
  }

  RB.views = RB.views || {};
  RB.views.reglas = {
    init: init,
    enter() {
      // Si el motor ya está listo cuando se llega aquí, se dibuja ahora.
      if (RB.engine.state === "ready") drawAll();
    },
  };
})();
