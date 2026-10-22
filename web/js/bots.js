/* La página de Bots: una ficha por cada jugador del registro.
 *
 * Los datos (nombre, emoji, autores y descripción) salen del puente de Python, que los lee de
 * cada clase de jugador: esta página no tiene la lista escrita a mano, así que un bot nuevo
 * aparece solo en cuanto se admite en players/.
 *
 * Todo el texto llega de código ajeno, así que se pone siempre con textContent (nunca como
 * HTML) y el CSS está pensado para nombres, autores y descripciones largos.
 */
(function () {
  "use strict";

  const RB = window.RB;
  const h = RB.h;
  let grid;
  let count;

  function plural(n) {
    return n === 1 ? "1 jugador admitido" : n + " jugadores admitidos";
  }

  function play(player) {
    // Lleva a la pantalla de juego y empieza una partida contra este bot (si no hay otra en curso).
    location.hash = "#/jugar";
    if (RB.views.jugar && RB.views.jugar.playAgainst) RB.views.jugar.playAgainst(player.name);
  }

  function card(player) {
    const authors = player.authors.length ? player.authors.join(", ") : "Sin autor declarado";
    return h("article", { class: "bot-card" },
      h("div", { class: "bot-card__head" },
        h("span", { class: "bot-card__icon", "aria-hidden": "true", text: player.icon }),
        h("div", { class: "bot-card__id" },
          h("h2", { class: "bot-card__name", text: player.name }),
          h("p", { class: "bot-card__authors", text: authors }),
        ),
      ),
      h("p", { class: "bot-card__desc", title: player.description, text: player.description }),
      h("button", { class: "btn btn--secondary btn--block", type: "button", onclick: () => play(player) },
        h("span", { class: "btn__label", text: "Jugar contra " + player.name }),
      ),
    );
  }

  /* Dibuja la lista. Se puede llamar con cualquier lista, también para probar casos extremos. */
  function render(players) {
    count.textContent = players.length ? plural(players.length) : "";
    if (!players.length) {
      grid.replaceChildren(h("p", { class: "bots__empty", text: "El registro no tiene ningún jugador. Añade un bot a la carpeta players/." }));
      return;
    }
    grid.replaceChildren(...players.map(card));
  }

  function fail(text) {
    count.textContent = "";
    grid.replaceChildren(h("p", { class: "bots__empty", role: "status", text: text }));
  }

  function init() {
    grid = document.getElementById("bots-grid");
    count = document.getElementById("bots-count");
    RB.engine.on("ready", (info) => render(info.players));
    RB.engine.on("fatal", (error) => fail("No se pudo cargar la lista de jugadores: " + error));
    RB.engine.on("restart", () => {
      count.textContent = "Cargando los jugadores del registro…";
      grid.replaceChildren(h("div", { class: "bot-card bot-card--skeleton", "aria-hidden": "true" }));
    });
  }

  RB.views = RB.views || {};
  RB.views.bots = { init: init, render: render };
})();
