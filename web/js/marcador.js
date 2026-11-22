/* El marcador: la clasificación del torneo (paso 5.5).
 *
 * No juega ninguna partida: descarga leaderboard.json, el archivo que deja el torneo nocturno
 * junto a la página (ver .github/workflows/pages.yml), y dibuja:
 *
 *   - el podio con los tres primeros, como carteles de «se busca»;
 *   - la tabla completa: partidas, % de victorias, fichas a favor y en contra, infracciones,
 *     y una marca en los bots que enviaron otros equipos;
 *   - el cara a cara: una cuadrícula de quién gana a quién, sacada de las partidas del archivo.
 *
 * La descarga usa { cache: "no-cache" } para que el navegador no enseñe la copia del día
 * anterior. Antes del primer torneo el archivo no existe: la página lo dice en vez de fallar.
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
  let datos = null;

  const $ = (id) => document.getElementById(id);
  const h = (...args) => RB.h(...args);
  const num = (value) => (Number.isFinite(value) ? value : 0);
  const fmt = (value, digits) => num(value).toLocaleString("es-ES", { maximumFractionDigits: digits === undefined ? 1 : digits });
  const pct = (part, total) => (total ? Math.round((100 * num(part)) / total) : 0);

  /* Los bots de otros equipos, según el registro que ya cargó la web (app.js). */
  function externos() {
    return new Set((RB.players || []).filter((p) => p.external).map((p) => p.name));
  }

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
    $("marcador-h2h").hidden = true;
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

  // ----------------------------------------------------------------- el podio --- //

  /* Los tres primeros, como carteles de «se busca» sobre su peana: el 1.º en el centro y más alto. */
  function poster(entry) {
    const crew = RB.crew.persona(entry);
    const pic = h("div", { class: "wanted__pic", "aria-hidden": "true" });
    RB.fillPic(pic, { name: entry.name, icon: entry.icon || "🏴‍☠️" }, "🏴‍☠️", crew);
    return h("article", { class: "marcador__cartel", dataset: { puesto: String(entry.rank) } },
      h("div", { class: "wanted paper" },
        h("div", { class: "wanted__top", text: "SE BUSCA", style: "font-size:2rem" }),
        h("span", { class: "marcador__medalla", text: "N.º " + entry.rank, "aria-hidden": "true" }),
        pic,
        h("div", { class: "wanted__sub", text: crew.aka.toUpperCase() }),
        h("div", { class: "wanted__name", text: entry.name }),
        h("div", { class: "wanted__money" }, h("span", { text: RB.crew.fmt(crew.bounty) }), h("small", { text: "BERRIES" })),
        h("div", { class: "wanted__foot", text: fmt(entry.points) + (entry.points === 1 ? " punto" : " puntos") + " · " + pct(entry.points, entry.played) + " % de victorias" }),
      ),
      h("div", { class: "marcador__peana", text: entry.rank + ".º", "aria-hidden": "true" }),
    );
  }

  // ----------------------------------------------------------------- la tabla --- //

  /* Sin autores, como el resto de la web salvo Rivales: aquí un bot es su estrategia. */
  function row(entry, fuera) {
    const diff = num(entry.disc_diff);
    const ganadas = pct(entry.points, entry.played);
    const infr = num(entry.forfeits);
    return h("tr", { dataset: { puesto: String(entry.rank) } },
      h("th", { scope: "row", class: "marcador__puesto", text: String(entry.rank) }),
      h("td", { class: "marcador__bot" },
        h("span", { class: "marcador__icono", "aria-hidden": "true", text: entry.icon || "" }),
        h("span", null,
          h("b", { text: entry.name }),
          h("small", { class: "marcador__alias" }, RB.crew.persona(entry).aka,
            fuera.has(entry.name) ? h("span", { class: "marcador__fuera", text: "de fuera" }) : null),
        ),
      ),
      h("td", { text: fmt(entry.played, 0) }),
      h("td", { class: "marcador__gep" },
        h("span", { class: "g", text: fmt(entry.wins, 0) }), " · ",
        h("span", { class: "e", text: fmt(entry.draws, 0) }), " · ",
        h("span", { class: "p", text: fmt(entry.losses, 0) })),
      h("td", { class: "marcador__barra" },
        h("span", { class: "barra", role: "img", "aria-label": ganadas + " % de los puntos posibles" },
          h("i", { style: "width:" + ganadas + "%" })),
        h("span", { class: "barra__n", text: ganadas + " %" })),
      h("td", { class: "marcador__pts", text: fmt(entry.points) }),
      h("td", { class: "marcador__fichas", text: fmt(entry.discs_for, 0) + " / " + fmt(entry.discs_against, 0) }),
      h("td", { class: diff > 0 ? "mas" : diff < 0 ? "menos" : "", text: (diff > 0 ? "+" : "") + fmt(diff, 0) }),
      h("td", { class: infr ? "menos" : "", text: infr ? fmt(infr, 0) : "—" }),
    );
  }

  // ------------------------------------------------------------- cara a cara --- //

  /* Cuenta, para cada pareja, cuántas veces gana cada uno. Sale de las partidas del archivo. */
  function cruces(partidas) {
    const mapa = new Map();
    const clave = (a, b) => a + "\u0000" + b;
    partidas.forEach((rec) => {
      if (!rec || typeof rec.black !== "string" || typeof rec.white !== "string") return;
      [[rec.black, rec.white], [rec.white, rec.black]].forEach(([a, b]) => {
        const k = clave(a, b);
        if (!mapa.has(k)) mapa.set(k, { gana: 0, pierde: 0, empata: 0 });
        const c = mapa.get(k);
        if (rec.winner === a) c.gana++; else if (rec.winner === b) c.pierde++; else c.empata++;
      });
    });
    return { get: (a, b) => mapa.get(clave(a, b)) };
  }

  function headToHead(standings, partidas) {
    const box = $("marcador-h2h");
    if (!Array.isArray(partidas) || !partidas.length || standings.length < 2) { box.hidden = true; return; }
    const tabla = cruces(partidas);
    const nombres = standings.map((entry) => entry.name);
    const iconos = new Map(standings.map((entry) => [entry.name, entry.icon || "🏴‍☠️"]));
    const cabecera = h("tr", null, h("th", { scope: "col", class: "h2h__esq", text: "Fila contra columna" }),
      ...nombres.map((n) => h("th", { scope: "col", title: n }, h("span", { class: "h2h__icono", text: iconos.get(n) }), h("span", { class: "h2h__corto", text: n }))));
    const filas = nombres.map((a) => h("tr", null,
      h("th", { scope: "row" }, h("span", { class: "h2h__icono", text: iconos.get(a) }), " ", a),
      ...nombres.map((b) => {
        if (a === b) return h("td", { class: "h2h__yo", text: "—" });
        const c = tabla.get(a, b);
        if (!c) return h("td", { class: "h2h__nada", text: "·" });
        const jugadas = c.gana + c.pierde + c.empata;
        const tono = jugadas ? (c.gana - c.pierde) / jugadas : 0;
        return h("td", null, h("span", {
          class: "h2h__celda", style: "--tono:" + tono.toFixed(2),
          title: a + " contra " + b + ": gana " + c.gana + ", pierde " + c.pierde + (c.empata ? ", empata " + c.empata : ""),
        }, h("b", { text: c.gana + "–" + c.pierde }), c.empata ? h("small", { text: " (" + c.empata + " E)" }) : null));
      }),
    ));
    $("h2h-grid").replaceChildren(h("table", { class: "h2h" }, h("thead", null, cabecera), h("tbody", null, ...filas)));
    box.hidden = false;
  }

  // ------------------------------------------------------------- infracciones --- //

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
    datos = data;
    clear();
    const standings = data.standings.map((s, i) => Object.assign({ rank: i + 1 }, s));
    if (!standings.length) {
      $("marcador-info").textContent = "Sin participantes";
      setMessage("El torneo se jugó, pero no había ningún bot en el registro.");
      return;
    }
    const when = whenText(data.finished_at);
    const partidas = Array.isArray(data.games) ? data.games : [];
    $("marcador-info").textContent = (when ? "Torneo del " + when + " · " : "")
      + fmt(data.rounds, 0) + (data.rounds === 1 ? " ronda" : " rondas")
      + (partidas.length ? " · " + fmt(partidas.length, 0) + " partidas" : "") + " · semilla " + fmt(data.seed, 0);
    $("marcador-podio").replaceChildren(...standings.slice(0, 3).map(poster));
    const fuera = externos();
    $("marcador-filas").replaceChildren(...standings.map((entry) => row(entry, fuera)));
    $("marcador-tabla").hidden = false;
    headToHead(standings, partidas);
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

  // Cuando el registro termina de cargar, la marca «de fuera» ya se puede poner.
  RB.marcadorRefresh = () => { if (datos && document.documentElement.dataset.view === "marcador") render(datos); };

  RB.marcador = { enter: enter, render: render };
})();
