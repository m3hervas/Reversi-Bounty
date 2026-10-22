/* Web Worker: ejecuta el motor de Python con Pyodide en un hilo aparte.
 *
 * Por qué un worker: Python tarda unos segundos en arrancar y un bot puede tardar en
 * pensar. En un hilo aparte la página nunca se congela, y si un bot se cuelga basta con
 * tirar el worker y crear otro (ver engine.js).
 *
 * Arranque: descarga Pyodide de su CDN, instala PyYAML (lo necesita el registro), descarga
 * py.zip (lo crea scripts/build_web.py), lo descomprime, importa webglue y carga el
 * registro de jugadores.
 *
 * Protocolo (todo lo que cruza hacia Python es texto JSON):
 *
 *   página → worker   { id, fn, args }              args: lista de textos JSON
 *   worker → página   { id, ok: true, result }      la respuesta de webglue, ya parseada
 *                     { id, ok: false, error }
 *                     { type: "status", text }      progreso del arranque
 *                     { type: "ready", players, python, pyodide }
 *                     { type: "fatal", error }      el arranque ha fallado
 */
/* global loadPyodide, importScripts */
"use strict";

var PYODIDE_VERSION = "0.29.3";
var PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v" + PYODIDE_VERSION + "/full/";
var LIB = "/home/pyodide/reversibounty-web";

var webglue = null;
var publicas = [];

function status(text) {
  self.postMessage({ type: "status", text: text });
}

/* Una respuesta de webglue es siempre { ok, result } o { ok: false, error }. */
function leer(texto) {
  var respuesta = JSON.parse(texto);
  if (!respuesta.ok) throw new Error(respuesta.error);
  return respuesta.result;
}

async function boot() {
  status("Descargando Python…");
  try {
    importScripts(PYODIDE_CDN + "pyodide.js");
  } catch (err) {
    throw new Error("No se pudo descargar Pyodide. ¿Hay conexión a internet?");
  }
  var pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });

  status("Instalando PyYAML…");
  await pyodide.loadPackage("pyyaml");

  status("Cargando el motor…");
  // «no-cache» revalida con el servidor: tras publicar un motor nuevo no se usa el viejo.
  var resp = await fetch(new URL("../py.zip", self.location.href), { cache: "no-cache" });
  if (!resp.ok) {
    throw new Error("No se encontró py.zip (HTTP " + resp.status + "). Genéralo con: python scripts/build_web.py");
  }
  pyodide.FS.mkdirTree(LIB);
  pyodide.unpackArchive(await resp.arrayBuffer(), "zip", { extractDir: LIB });
  pyodide.runPython("import sys\nsys.path.insert(0, " + JSON.stringify(LIB) + ")");

  status("Leyendo el registro de jugadores…");
  webglue = pyodide.pyimport("webglue");
  publicas = webglue.__all__.toJs();
  var players = leer(webglue.init(JSON.stringify(LIB + "/players")));
  var python = pyodide.runPython("import sys\nsys.version.split()[0]");
  self.postMessage({ type: "ready", players: players, python: python, pyodide: PYODIDE_VERSION });
}

var booting = boot().catch(function (err) {
  var text = String(err && err.message ? err.message : err).trim().split("\n").pop();
  self.postMessage({ type: "fatal", error: text });
  throw err;
});

self.onmessage = async function (event) {
  var msg = event.data;
  try {
    await booting;
    // Solo las funciones que webglue declara públicas en __all__.
    if (publicas.indexOf(msg.fn) === -1) throw new Error("Función desconocida: " + msg.fn);
    var result = leer(webglue[msg.fn].apply(null, msg.args || []));
    self.postMessage({ id: msg.id, ok: true, result: result });
  } catch (err) {
    self.postMessage({ id: msg.id, ok: false, error: String(err && err.message ? err.message : err) });
  }
};
