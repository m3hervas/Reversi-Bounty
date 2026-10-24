/* La página: rutas por hash, tema, sonido, cartel personal, tablón de rivales y utilidades.
 *
 * Rutas (igual que el proyecto): #/jugar  #/reglas  #/bots  #/anadir  y #/ para la portada.
 * El estado de la vista vive en <html data-view>; el CSS enseña la sección que toca.
 * El motor de Python se arranca en cuanto carga la página: así, cuando alguien llega a
 * «Lucha», el motor ya está listo.
 */
(function () {
  "use strict";

  const RB = window.RB;
  const crew = RB.crew;
  const VIEWS = ["inicio", "jugar", "reglas", "bots", "anadir"];
  const $ = (id) => document.getElementById(id);

  /* h("div", { class: "x", text: "…" }, hijo, …) */
  RB.h = function h(tag, attrs, ...children) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([key, value]) => {
      if (value === null || value === undefined || value === false) return;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key === "dataset") Object.assign(node.dataset, value);
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    });
    children.flat().forEach((c) => { if (c !== null && c !== undefined && c !== false) node.append(c instanceof Node ? c : document.createTextNode(String(c))); });
    return node;
  };
  const h = RB.h;

  // ------------------------------------------------------------------ sonido --- //

  const sound = { on: true, ctx: null };
  try { sound.on = localStorage.getItem("bb-sonido") !== "off"; } catch (e) { /* ok */ }

  function tone(freq, start, dur, type, gain) {
    const ctx = sound.ctx;
    const osc = ctx.createOscillator();
    const amp = ctx.createGain();
    osc.type = type || "triangle";
    osc.frequency.setValueAtTime(freq, ctx.currentTime + start);
    amp.gain.setValueAtTime(0.0001, ctx.currentTime + start);
    amp.gain.exponentialRampToValueAtTime(gain || 0.12, ctx.currentTime + start + 0.01);
    amp.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + dur);
    osc.connect(amp).connect(ctx.destination);
    osc.start(ctx.currentTime + start);
    osc.stop(ctx.currentTime + start + dur + 0.05);
  }

  sound.play = function (kind, extra) {
    if (!sound.on) return;
    try {
      sound.ctx = sound.ctx || new (window.AudioContext || window.webkitAudioContext)();
      if (sound.ctx.state === "suspended") sound.ctx.resume();
      if (kind === "move") {
        tone(220, 0, 0.09, "square", 0.05);
        const n = Math.min((extra && extra.flips) || 0, 6);
        for (let i = 0; i < n; i++) tone(440 + i * 70, 0.08 + i * 0.05, 0.1, "triangle", 0.08);
      } else if (kind === "pass") { tone(300, 0, 0.18, "sine"); tone(240, 0.16, 0.22, "sine"); }
      else if (kind === "win") [523, 659, 784, 1047, 1319].forEach((f, i) => tone(f, i * 0.11, 0.3, "triangle", 0.12));
      else if (kind === "lose") [392, 330, 262, 196].forEach((f, i) => tone(f, i * 0.16, 0.34, "sawtooth", 0.06));
      else if (kind === "draw") { tone(392, 0, 0.25); tone(392, 0.28, 0.35); }
      else if (kind === "stamp") { tone(110, 0, 0.18, "square", 0.14); tone(80, 0.05, 0.25, "sawtooth", 0.08); }
    } catch (e) { /* sin audio: no pasa nada */ }
  };
  RB.sound = sound;

  function syncSoundBtn() {
    const btn = $("sound-btn");
    btn.dataset.on = String(sound.on);
    btn.setAttribute("aria-pressed", String(sound.on));
    btn.setAttribute("aria-label", sound.on ? "Silenciar los sonidos" : "Activar los sonidos");
  }

  // -------------------------------------------------------------------- tema --- //

  function toggleTheme() {
    const d = document.documentElement;
    const dark = d.dataset.theme ? d.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    d.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("bb-tema", d.dataset.theme); } catch (e) { /* ok */ }
  }

  // ------------------------------------------------------------------ router --- //

  function route() {
    const m = /^#\/?([a-z-]*)/.exec(location.hash);
    const name = m && VIEWS.includes(m[1]) && m[1] ? m[1] : "inicio";
    document.documentElement.dataset.view = name;
    const titles = { inicio: "Reversi Bounty · Grand Line", jugar: "Lucha", reglas: "Leyes del mar", bots: "Rivales", anadir: "Añade tu Bot" };
    document.title = name === "inicio" ? titles.inicio : titles[name] + " · Reversi Bounty";
    window.scrollTo(0, 0);
    const heading = document.querySelector('.view[data-view="' + name + '"] [tabindex="-1"]');
    if (heading) heading.focus({ preventScroll: true });
  }

  // ----------------------------------------------------------- cartel personal --- //

  function renderProfile(stamp) {
    const p = crew.profile;
    $("my-name").textContent = p.name || "Capitán Anónimo";
    $("my-berries").textContent = crew.fmt(p.berries);
    $("st-w").textContent = p.w; $("st-d").textContent = p.d; $("st-l").textContent = p.l;
    const r = crew.rank(p.berries);
    $("rank-txt").textContent = "Rango: " + r.title;
    $("rank-next").textContent = r.next ? "Te faltan " + crew.fmt(r.nextAt - p.berries) + " berries para «" + r.next + "»." : "Has llegado a lo más alto del mar.";
    $("rank-bar").setAttribute("aria-valuenow", String(r.pct));
    $("rank-bar").firstElementChild.style.width = r.pct + "%";
    if (stamp) {
      const s = $("my-stamp");
      s.classList.remove("on");
      void s.offsetWidth;
      s.classList.add("on");
      setTimeout(() => s.classList.remove("on"), 2400);
    }
  }
  RB.renderProfile = renderProfile;

  /* Una victoria, un empate o una derrota de la persona frente a un bot. Devuelve los berries ganados. */
  RB.recordResult = function (bot, outcome, diff) {
    const p = crew.profile;
    const earned = crew.reward(bot, diff, outcome);
    p.berries += earned;
    if (outcome === "win") p.w++; else if (outcome === "draw") p.d++; else p.l++;
    crew.save();
    renderProfile(false);
    return earned;
  };

  // ------------------------------------------------------- tablón de rivales --- //

  /* La foto del cartel: si el rival tiene personaje, una "pantalla de selección" translúcida con
   * él de pie; si no (un bot nuevo del registro), su emoji de siempre. */
  RB.fillPic = function (el, bot, fallback, persona) {
    const p = persona || crew.persona(bot);
    el.classList.toggle("sel", !!(bot && p.img));
    el.style.removeProperty("--c");
    if (!bot || !p.img) { el.replaceChildren(document.createTextNode(bot ? bot.icon : fallback)); return; }
    el.style.setProperty("--c", p.accent);
    el.replaceChildren(
      h("i", { class: "sel__floor" }),
      h("img", { class: "sel__char", src: p.img, alt: "", width: "300", height: "400", decoding: "async" }),
      h("i", { class: "sel__shine" }),
      h("span", { class: "sel__tag", text: bot.icon }),
    );
  };

  function wantedCard(bot, extra) {
    const p = crew.persona(bot);
    const pic = h("div", { class: "wanted__pic", "aria-hidden": "true" });
    RB.fillPic(pic, bot, "🏴‍☠️");
    return h("article", { class: "rival" },
      h("div", { class: "wanted paper" },
        h("div", { class: "wanted__top", text: "SE BUSCA", style: "font-size:2rem" }),
        pic,
        h("div", { class: "wanted__sub", text: p.aka.toUpperCase() }),
        h("div", { class: "wanted__name", text: bot.name }),
        h("div", { class: "wanted__money" }, h("span", { text: crew.fmt(p.bounty) }), h("small", { text: "BERRIES" })),
      ),
      h("p", { class: "rival__desc", text: bot.description }),
      extra,
    );
  }

  function renderRivals(players) {
    const box = $("rivals");
    box.replaceChildren(...players.map((bot) => wantedCard(bot,
      h("a", { class: "btn btn--sm", href: "#/jugar", onclick: () => RB.play && RB.play.challenge(bot.name), text: "¡Retarlo!" }))));
    $("bots-count").textContent = players.length + (players.length === 1 ? " rival admitido" : " rivales admitidos") + " en el registro";
  }

  // ------------------------------------------------- mini tableros de las reglas --- //

  /* . vacía · h sombrero · s calavera · t jugada · S calavera volteada · H sombrero volteado
   · mapa: K tesoro · X torbellino · C arrecife · E costa */
  function renderMinis() {
    document.querySelectorAll("[data-mini]").forEach((box) => {
      const rows = box.dataset.mini.split("|");
      const cells = [];
      rows.forEach((row) => Array.from(row).forEach((ch) => {
        const cls = { h: "h", s: "s", t: "t", S: "s f", H: "h f", K: "k", X: "x", C: "c", E: "e" }[ch] || "";
        cells.push(h("i", { class: cls }));
      }));
      box.replaceChildren(...cells);
      box.setAttribute("role", "img");
      box.setAttribute("aria-label", "Tablero de ejemplo");
    });
  }

  // ------------------------------------------------------------------- init --- //

  function init() {
    syncSoundBtn();
    $("sound-btn").addEventListener("click", () => {
      sound.on = !sound.on;
      try { localStorage.setItem("bb-sonido", sound.on ? "on" : "off"); } catch (e) { /* ok */ }
      syncSoundBtn();
      if (sound.on) sound.play("move", { flips: 2 });
    });
    $("theme-btn").addEventListener("click", toggleTheme);

    window.addEventListener("hashchange", route);
    route();

    const nameIn = $("name-in");
    nameIn.value = crew.profile.name;
    nameIn.addEventListener("input", () => { crew.profile.name = nameIn.value.trim(); crew.save(); renderProfile(false); if (RB.refreshPosters) RB.refreshPosters(); });
    renderProfile(false);
    renderMinis();

    document.querySelectorAll("[data-copy]").forEach((btn) => btn.addEventListener("click", async () => {
      const text = $("code-" + btn.dataset.copy).textContent;
      try { await navigator.clipboard.writeText(text); btn.textContent = "¡Copiado!"; } catch (e) { btn.textContent = "Selecciona y copia"; }
      setTimeout(() => { btn.textContent = "Copiar"; }, 1800);
    }));

    const chip = $("engine-chip");
    RB.engine.on("status", (t) => { $("engine-text").textContent = t; });
    RB.engine.on("ready", (info) => {
      chip.dataset.state = "ready";
      $("engine-text").textContent = "Python " + info.python;
      $("footer-engine").textContent = "Las reglas y los bots son el paquete Python del proyecto: Python " + info.python + " con Pyodide " + info.pyodide + ", cargado en " + (info.ms / 1000).toFixed(1) + " s.";
      renderRivals(info.players);
    });
    RB.engine.on("fatal", (msg) => {
      chip.dataset.state = "error";
      $("engine-text").textContent = "Sin motor";
      $("bots-count").textContent = "No se pudo cargar el registro: " + msg;
      $("rivals").replaceChildren();
    });
    RB.engine.start();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
