/* El motor: la única puerta de la página hacia Python (fachada del Web Worker).
 *
 *   RB.engine.start()                         arranca el worker (solo la primera vez)
 *   RB.engine.ready                           promesa: { players, python, pyodide, ms }
 *   RB.engine.call(fn, args, { timeout })     promesa con el resultado de webglue.fn
 *   RB.engine.restart()                       tira el worker y arranca otro
 *   RB.engine.on(evento, fn)                  "status" | "ready" | "fatal" | "restart"
 *
 * Todas las llamadas convierten cada argumento a JSON antes de mandarlo: el puente de
 * Python solo recibe y devuelve texto JSON. Ningún otro archivo habla con el worker.
 */
(function () {
  "use strict";

  const RB = (window.RB = window.RB || {});
  const WORKER_URL = "js/worker.js?v=2";
  const listeners = { status: [], ready: [], fatal: [], restart: [] };
  const pending = new Map();
  let worker = null;
  let nextId = 1;
  let settle = null;

  const engine = {
    state: "idle", // idle | loading | ready | error
    statusText: "",
    info: null,
    error: null,
    ready: null,
  };

  function freshReady() {
    engine.ready = new Promise((resolve, reject) => { settle = { resolve, reject }; });
    engine.ready.catch(() => {}); // quien no espere al motor no debe ver un error sin capturar
  }
  freshReady();

  function emit(type, payload) {
    listeners[type].forEach((fn) => {
      try { fn(payload); } catch (err) { RB.reportError(err); }
    });
  }

  function fail(message) {
    if (engine.state === "error") return;
    engine.state = "error";
    engine.error = message;
    settle.reject(new Error(message));
    pending.forEach((entry) => entry.reject(new Error(message)));
    pending.clear();
    emit("fatal", message);
  }

  function start() {
    if (worker) return;
    engine.state = "loading";
    const started = performance.now();
    try {
      worker = new Worker(WORKER_URL);
    } catch (err) {
      // Pasa al abrir index.html con doble clic (file://): el navegador no deja crear workers.
      fail(location.protocol === "file:"
        ? "Abre la web con un servidor local: python -m http.server -d web"
        : "Este navegador no puede ejecutar el motor (" + err.message + ")");
      return;
    }
    worker.onmessage = (event) => {
      const msg = event.data;
      if (msg.type === "status") {
        engine.statusText = msg.text;
        emit("status", msg.text);
      } else if (msg.type === "ready") {
        engine.state = "ready";
        engine.info = {
          players: msg.players,
          python: msg.python,
          pyodide: msg.pyodide,
          ms: Math.round(performance.now() - started),
        };
        settle.resolve(engine.info);
        emit("ready", engine.info);
      } else if (msg.type === "fatal") {
        fail(msg.error);
      } else {
        const entry = pending.get(msg.id);
        if (!entry) return; // respuesta de una llamada que ya caducó
        pending.delete(msg.id);
        clearTimeout(entry.timer);
        if (msg.ok) entry.resolve(msg.result);
        else entry.reject(new Error(msg.error));
      }
    };
    worker.onerror = (event) => {
      event.preventDefault();
      fail(event.message || "No se pudo cargar el motor");
    };
  }

  /**
   * Llama a una función de webglue.py. Con `timeout` (ms), si Python no contesta a
   * tiempo la promesa falla con err.code === "timeout" y el worker se reinicia: no hay
   * forma de interrumpir a Python a mitad de una función.
   */
  function call(fn, args, opts) {
    if (!worker) start();
    if (engine.state === "error") return Promise.reject(new Error(engine.error));
    const timeout = opts && opts.timeout;
    return new Promise((resolve, reject) => {
      const id = nextId++;
      const entry = { resolve, reject, timer: null };
      if (timeout) {
        entry.timer = setTimeout(() => {
          pending.delete(id);
          const err = new Error("El motor no ha respondido en " + Math.round(timeout / 1000) + " s");
          err.code = "timeout";
          reject(err);
          restart();
        }, timeout);
      }
      pending.set(id, entry);
      worker.postMessage({ id, fn, args: (args || []).map((a) => JSON.stringify(a)) });
    });
  }

  function restart() {
    if (worker) worker.terminate();
    worker = null;
    pending.forEach((entry) => { clearTimeout(entry.timer); entry.reject(new Error("Motor reiniciado")); });
    pending.clear();
    engine.state = "idle";
    engine.info = null;
    engine.error = null;
    freshReady();
    emit("restart");
    start();
    return engine.ready;
  }

  engine.start = start;
  engine.call = call;
  engine.restart = restart;
  engine.on = (type, fn) => { listeners[type].push(fn); };
  RB.engine = engine;
})();
