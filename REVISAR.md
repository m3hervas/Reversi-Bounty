# Por revisar: código innecesario

Revisión del motor, bots, registro, puente web y JS principal. Pendiente de revisar a fondo: `play.js`, `sound.js`, CSS, `index.html`, tests y docs.

## Recortes seguros

1. `players` en `web/webglue.py`: la web no lo llama (solo los tests). `legal_moves` NO quitarlo: la guía (4.2) pide poder pedir movimientos legales desde la consola del navegador y el README lo usa de ejemplo.
2. `replace(state)` en `request_move` (`match.py`): `GameState` es inmutable, copiarlo no protege. Sustituir también el `Mover` Protocol por `Player`.
3. `web/js/engine.js`: `engine.ready`, `freshReady`, `settle` y `statusText` no los usa nadie.
4. `RB.views.bots.render` exportado solo «para probar casos extremos»: dejarlo privado si nada más lo usa.
5. `_jugada` y `_entero` en el puente repiten `_as_move`/`is_legal` de `game.py`: dejar que decida el motor.
6. `_has_moves` y `_moves_for` en `game.py` son casi la misma función; unificar. `__version__` está duplicado con `pyproject.toml`.

## Exceso de texto

- Docstrings de módulo de 25-30 líneas (`game.py`, `manifest.py`, `build_web.py`, `webglue.py`) y `Args/Returns` en funciones triviales (`opponent`, `color_name`, `score`): comprimir.
- `scripts/build_web.py` puede quedar en ~40 líneas (sobran `--out`, separar `contenido`/`build`, parámetro `raiz`).

## Decisiones pendientes

- `terminal.py` (335 líneas): la guía (1.5) exige jugar en terminal, así que NO se quita; solo se puede reducir (por ejemplo, un único modo de dibujo).
- Portada precalculada (`generar_portada.py`, `portada.json`, `test_portada.py`, promesa en `app.js`): quitar y dejar el tablero inicial.
- Boilerplate de bots: cuatro `classmethod` (`get_name`...) por atributos de clase. Cambia API, docs y tests.
- `sound.js` (157 líneas) y `toc.js`: ¿esenciales?
- `manifest.py`: regex de emoji y validación del YAML; proteger las PR, probablemente mantener.

Nota: hay muchos cambios sin commitear; hacer commit antes de recortar.
