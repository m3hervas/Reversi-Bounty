/* Arranque de la página: rutas, tema, indicador del motor y portada.
 *
 * Rutas por hash (#/jugar): la web es un solo index.html servido tal cual, sin servidor
 * que entienda direcciones como /jugar. Cada apartado es:
 *   1. una entrada en ROUTES,
 *   2. una <section class="view" data-view="nombre"> en index.html,
 *   3. un enlace en la navegación,
 *   4. opcionalmente, un módulo RB.views.nombre = { init(), enter() } en su propio .js.
 * Para añadir un apartado nuevo (Torneo, por ejemplo) no hay que tocar nada de lo que ya existe.
 *
 * Cada parte arranca por separado (ver `safe`): si una falla, se avisa y las demás siguen.
 */
(function () {
  "use strict";

  const RB = window.RB;
  const ROUTES = {
    "": { view: "inicio", title: "Reversi Bounty" },
    jugar: { view: "jugar", title: "Jugar · Reversi Bounty" },
    reglas: { view: "reglas", title: "Reglas · Reversi Bounty" },
    bots: { view: "bots", title: "Bots · Reversi Bounty" },
  };
  const THEME_KEY = "rb-tema";
  const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

  function safe(name, fn) {
    try { fn(); } catch (err) { RB.reportError(new Error("No se pudo iniciar «" + name + "»: " + err.message)); }
  }

  // ------------------------------------------------------------------ rutas --- //

  let current = null;
  function route() {
    const match = /^#\/?([a-z-]*)/.exec(location.hash);
    let name = match ? match[1] : "";
    if (!(name in ROUTES)) {
      name = "";
      history.replaceState(null, "", "#/"); // una dirección desconocida lleva a la portada
    }
    const { view, title } = ROUTES[name];
    const first = current === null;
    document.documentElement.dataset.view = view;
    document.title = title;
    document.querySelectorAll(".nav a").forEach((a) => {
      if (a.dataset.route === view) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    if (view !== current) {
      current = view;
      if (!first) {
        // Al cambiar de apartado: arriba del todo y el foco en el título (lectores de pantalla).
        window.scrollTo(0, 0);
        const heading = document.querySelector('.view[data-view="' + view + '"] h1');
        if (heading) heading.focus({ preventScroll: true });
      }
      const module = RB.views && RB.views[view];
      if (module && module.enter) module.enter();
    }
  }

  // ------------------------------------------------------------------- tema --- //

  /* Por defecto sigue al sistema. Al pulsar el botón se fija el contrario y se guarda. */
  function effectiveTheme() {
    return document.documentElement.dataset.theme || (darkQuery.matches ? "dark" : "light");
  }

  function paintThemeButton() {
    const btn = document.getElementById("theme-btn");
    const dark = effectiveTheme() === "dark";
    btn.dataset.current = dark ? "dark" : "light";
    btn.setAttribute("aria-label", dark ? "Cambiar a tema claro" : "Cambiar a tema oscuro");
  }

  function initTheme() {
    document.getElementById("theme-btn").addEventListener("click", () => {
      const next = effectiveTheme() === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* no se recordará */ }
      paintThemeButton();
    });
    darkQuery.addEventListener("change", paintThemeButton);
    paintThemeButton();
  }

  // -------------------------------------------------------------- motor --- //

  function initEngineChip() {
    const chip = document.getElementById("engine-chip");
    const text = document.getElementById("engine-chip-text");
    const set = (state, label, title) => {
      chip.dataset.state = state;
      text.textContent = label;
      if (title) chip.title = title;
    };
    RB.engine.on("status", (msg) => set("loading", "Python…", msg));
    RB.engine.on("restart", () => set("loading", "Python…", "Reiniciando el motor"));
    RB.engine.on("fatal", (err) => set("error", "Sin motor", err));
    RB.engine.on("ready", (info) => {
      set("ready", "Python " + info.python, "Python " + info.python + " con Pyodide " + info.pyodide + ", listo en " + (info.ms / 1000).toFixed(1) + " s");
      document.getElementById("footer-engine").textContent =
        "Las reglas y los bots son el paquete Python del proyecto: Python " + info.python + " con Pyodide " + info.pyodide + ", en tu navegador.";
    });
  }

  // ------------------------------------------------------------- portada --- //

  /* Una apertura jugada por el motor de verdad: prueba visible de que Python está corriendo. */
  const OPENING = ["f5", "d6", "c3", "d3", "c4"];

  function initHero() {
    const host = document.getElementById("hero-board");
    const caption = document.getElementById("hero-caption");
    RB.paintBoard(host, null, { label: "Tablero vacío" });
    RB.engine.on("fatal", () => { caption.textContent = "No se pudo arrancar el motor de Python."; });
    RB.engine.on("ready", async () => {
      try {
        let view = await RB.engine.call("new_game");
        for (const move of OPENING) view = await RB.engine.call("play_move", [view.state, move]);
        RB.paintBoard(host, view, { last: view.move, label: "Tablero tras la apertura " + OPENING.join(" ") });
        caption.textContent = "La apertura del tigre (" + OPENING.join(" ") + "), jugada ahora mismo por el motor de Python en tu navegador.";
      } catch (err) {
        caption.textContent = "El motor no pudo jugar la apertura: " + err.message;
      }
    });
  }

  // ------------------------------------------------------------- arranque --- //

  function boot() {
    safe("el tema", initTheme);
    safe("el sonido", () => RB.sound.init());
    safe("el indicador del motor", initEngineChip);
    safe("la portada", initHero);
    Object.entries(RB.views || {}).forEach(([name, module]) => {
      if (module.init) safe(name, module.init);
    });
    safe("las rutas", () => {
      window.addEventListener("hashchange", route);
      route();
    });
    RB.engine.start(); // el último paso: cuando ya escucha todo el mundo
  }

  boot();
})();
