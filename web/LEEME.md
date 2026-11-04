# La web, en local

Esta carpeta es una página estática. Los jugadores no necesitan nada de esto: la web pública está
en <https://m3hervas.github.io/Reversi-Bounty/>. Esto es para quien quiera tocar la web.

```bash
python scripts/build_web.py          # empaqueta el motor en web/py.zip
python -m http.server 8000 -d web    # sirve la carpeta web/
```

Abre <http://localhost:8000>. No abras `index.html` con doble clic: con `file://` el navegador no
deja arrancar el motor. Vuelve a ejecutar `build_web.py` cada vez que cambies el motor, un bot o
`web/webglue.py`. `web/py.zip` es un archivo generado y no se sube al repositorio.

No reimplementa ninguna regla: ejecuta en el navegador, con [Pyodide](https://pyodide.org), el
mismo paquete `reversibounty` que usan los tests.

## Qué hay dentro

```
index.html        las siete vistas (portada, lucha, aprende, rivales, marcador, reglas, añade tu bot)
css/              theme.css (base), pages.css (páginas) y play.css (la partida)
js/engine.js      la puerta de la página hacia el motor de Python
js/worker.js      Pyodide en un hilo aparte
js/crew.js        alias, frases y recompensas de cada rival
js/marcador.js    la clasificación del torneo (descarga leaderboard.json y dibuja la tabla)
js/tutorial.js    Aprende jugando: las lecciones de data/tutorial.json sobre el tablero
data/tutorial.json las lecciones: posición, jugadas obligadas y frases del mentor
js/app.js         rutas, tema, sonido, cartel personal y tablón de rivales
js/play.js        la partida
img/              los retratos de los personajes (PNG con fondo transparente)
webglue.py        el puente entre JavaScript y el motor
```

Para cambiar una lección del tutorial, edita `data/tutorial.json`: el tablero va en ocho filas con
`X` (calaveras, el jugador), `O` (sombreros, el rival) y `.` (vacía). En una lección `guion`, cada
paso dice quién juega (`tu` o `rival`), la casilla (`d3`) y la frase del mentor; el jugador solo
puede pulsar esa casilla. Un paso `volver` (sin casilla) explica el error y, con el botón «Volver
atrás», devuelve el tablero a la posición de partida para probar la jugada buena. Una lección
`libre` no tiene pasos: se juega de verdad contra el bot del registro que diga `rival`, con
cualquier jugada legal, y tras cada una el mentor dice cuántas fichas puede quitarte el rival en su
respuesta (lo calcula el motor con `coach`). Si ganas se ve `win`; si no, `lose` y «Reintentar». `tests/test_web_tutorial.py` reproduce cada lección con el motor y falla
si alguna jugada no es legal o no es su turno.

Para añadir un personaje: pon su PNG con fondo transparente en `img/` y una entrada en `js/crew.js`
con el **nombre exacto** del bot (el que devuelve `get_name()`). Más en
[el diseño de la web](../docs/diseno-jugar.md).
