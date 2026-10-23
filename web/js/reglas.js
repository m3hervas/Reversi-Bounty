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

  function init() {
    showPlaceholders();
    RB.toc("reglas");
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
