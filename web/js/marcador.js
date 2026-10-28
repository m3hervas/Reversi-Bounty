/* El marcador: la clasificación del torneo (paso 5.5).
 *
 * No juega ninguna partida: descarga leaderboard.json, el archivo que deja el torneo nocturno
 * junto a la página (ver .github/workflows/pages.yml), y dibuja la tabla. La descarga usa
 * { cache: "no-cache" } para que el navegador no enseñe la copia del día anterior. Antes del
 * primer torneo el archivo no existe: la página lo dice en vez de fallar.
 *
 * El archivo viene de fuera (los nombres y los motivos de infracción los escriben los bots),
 * así que todo texto se pone con textContent, nunca como HTML.
 *
 *   RB.marcador.enter()    se llama al entrar en #/marcador: vuelve a descargar el archivo
 *   RB.marcador.render(d)  dibuja unos datos ya leídos (sirve para probar casos extremos)
 */
(function () {
  "use strict";

  const RB = (window.RB = window.RB || {});
  const FILE = "leaderboard.json";
  const SCHEMA = 1;
  const MAX_MOTIVOS = 3;
  let loading = false;

  const $ = (id) => document.getElementById(id);
  const h = (...args) => RB.h(...args);
  const num = (value) => (Number.isFinite(value) ? value : 0);
  const fmt = (value, digits) => num(value).toLocaleString("es-ES", { maximumFractionDigits: digits === undefined ? 1 : digits });

  function setMessage(text, retry) {
    const box = $("marcador-msg");
    box.replaceChildren(h("p", { text: text }));
    if (retry) box.append(h("button", { class: "btn btn--sm", type: "button", onclick: enter, text: "Reintentar" }));
    box.hidden = false;
  }

  function clear() {
    $("marcador-msg").hidden = true;
    $("marcador-podio").replaceChildren();
    $("marcador-tabla").hidden = true;
    $("marcador-infr").hidden = true;
  }

  function fail(info, text, retry) {
    clear();
    $("marcador-info").textContent = info;
    setMessage(text, retry);
  }

  /* El archivo tiene la forma que esta página sabe leer: si no, mejor decirlo que dibujar basura. */
  function valid(data) {
    return !!data && data.schema_version === SCHEMA && Array.isArray(data.standings)
      && data.standings.every((s) => s && typeof s.name === "string");
  }

  function whenText(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleString("es-ES", { dateStyle: "long", timeStyle: "short" });
  }

  /* Los tres primeros, como carteles de «se busca»: la recompensa sale de crew.js. */
  function poster(entry) {
    const crew = RB.crew.persona(entry);
    const pic = h("div", { class: "wanted__pic", "aria-hidden": "true" });
    RB.fillPic(pic, { name: entry.name, icon: entry.icon || "🏴‍☠️" }, "🏴‍☠️", crew);
    return h("article", { class: "rival marcador__cartel", dataset: { puesto: String(entry.rank) } },
      h("div", { class: "wanted paper" },
        h("div", { class: "wanted__top", text: "SE BUSCA", style: "font-size:2rem" }),
        h("span", { class: "marcador__medalla", text: "N.º " + entry.rank, "aria-hidden": "true" }),
        pic,
        h("div", { class: "wanted__sub", text: crew.aka.toUpperCase() }),
        h("div", { class: "wanted__name", text: entry.name }),
        h("div", { class: "wanted__money" }, h("span", { text: RB.crew.fmt(crew.bounty) }), h("small", { text: "BERRIES" })),
        h("div", { class: "wanted__foot", text: "Puesto " + entry.rank + " · " + fmt(entry.points) + " puntos" }),
      ),
    );
  }

  function row(entry) {
    const authors = Array.isArray(entry.authors) && entry.authors.length ? entry.authors.join(", ") : "";
    const diff = num(entry.disc_diff);
    return h("tr", null,
      h("th", { scope: "row", class: "marcador__puesto", text: String(entry.rank) }),
      h("td", { class: "marcador__bot" },
        h("span", { class: "marcador__icono", "aria-hidden": "true", text: entry.icon || "" }),
        h("span", null,
          h("b", { text: entry.name }),
          authors ? h("small", { text: authors }) : null,
        ),
      ),
      h("td", { text: fmt(entry.played, 0) }),
      h("td", { text: fmt(entry.wins, 0) }),
      h("td", { text: fmt(entry.draws, 0) }),
      h("td", { text: fmt(entry.losses, 0) }),
      h("td", { class: "marcador__pts", text: fmt(entry.points) }),
      h("td", { text: (diff > 0 ? "+" : "") + fmt(diff, 0) }),
    );
  }

  /* Un bot que falla, se cuelga o hace trampas pierde esa partida: se cuenta aquí por qué. */
  function infractions(standings) {
    const box = $("marcador-infr");
    const guilty = standings.filter((s) => Array.isArray(s.forfeit_reasons) && s.forfeit_reasons.length);
    if (!guilty.length) { box.hidden = true; return; }
    box.replaceChildren(
      h("h2", { text: "Partidas perdidas por infracción" }),
      ...guilty.map((s) => {
        const reasons = s.forfeit_reasons.map(String);
        const extra = reasons.length - MAX_MOTIVOS;
        return h("div", { class: "marcador__motivo" },
          h("b", { text: s.name + " · " + reasons.length + (reasons.length === 1 ? " partida" : " partidas") }),
          h("ul", null,
            ...reasons.slice(0, MAX_MOTIVOS).map((r) => h("li", { text: r })),
            extra > 0 ? h("li", { text: "…y " + extra + " más" }) : null,
          ),
        );
      }),
    );
    box.hidden = false;
  }

  function render(data) {
    if (!valid(data)) {
      fail("No se pudo leer la clasificación", "El archivo del marcador no tiene la forma esperada. Prueba más tarde.", true);
      return;
    }
    clear();
    const standings = data.standings.map((s, i) => Object.assign({ rank: i + 1 }, s));
    if (!standings.length) {
      $("marcador-info").textContent = "Sin participantes";
      setMessage("El torneo se jugó, pero no había ningún bot en el registro.");
      return;
    }
    const when = whenText(data.finished_at);
    $("marcador-info").textContent = (when ? "Torneo del " + when + " · " : "")
      + fmt(data.rounds, 0) + (data.rounds === 1 ? " ronda" : " rondas") + " · semilla " + fmt(data.seed, 0);
    $("marcador-podio").replaceChildren(...standings.slice(0, 3).map(poster));
    $("marcador-filas").replaceChildren(...standings.map(row));
    $("marcador-tabla").hidden = false;
    infractions(standings);
  }

  function enter() {
    if (loading) return;
    loading = true;
    $("marcador-info").textContent = "Cargando la clasificación…";
    // no-cache: el navegador pregunta al servidor si el archivo cambió y no enseña la copia de ayer.
    fetch(FILE, { cache: "no-cache" })
      .then((response) => {
        if (response.status === 404) {
          fail("Todavía no hay clasificación",
            "Aún no se ha jugado ningún torneo. Se juega solo cada noche: vuelve mañana y aparecerán aquí los bots, con su puesto.");
          return null;
        }
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then((data) => { if (data) render(data); })
      .catch(() => fail("No se pudo cargar la clasificación",
        "No se ha podido descargar el marcador. Comprueba tu conexión e inténtalo de nuevo.", true))
      .finally(() => { loading = false; });
  }

  RB.marcador = { enter: enter, render: render };
})();
