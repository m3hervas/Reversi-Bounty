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
    anadir: { view: "anadir", title: "Añade tu bot · Reversi Bounty" },
  };
  const THEME_KEY = "rb-tema";
  /* Posiciones calculadas de antemano por el motor (scripts/generar_portada.py): se pintan al
   * instante, sin esperar a que Python arranque en el navegador, que son unos segundos. */
  RB.portada = fetch("data/portada.json?v=1").then((r) => (r.ok ? r.json() : null)).catch(() => null);
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

  /* La portada enseña una apertura ya calculada, así aparece al instante; mientras, el motor de
   * Python arranca detrás (el indicador de la cabecera avisa de cuándo está listo). */
  function initHero() {
    const host = document.getElementById("hero-board");
    const caption = document.getElementById("hero-caption");
    RB.paintBoard(host, null, { label: "Tablero vacío" });
    RB.portada.then((data) => {
      if (!data) {
        caption.textContent = "";
        return;
      }
      const opening = data.apertura.jugadas.join(" ");
      RB.paintBoard(host, data.apertura.vista, { last: data.apertura.vista.move, label: "Tablero tras la apertura " + opening });
      caption.textContent = "La apertura del tigre (" + opening + "), calculada por el motor de Python del proyecto.";
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
