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
index.html        las cinco vistas (portada, lucha, rivales, reglas, añade tu bot)
css/              theme.css (base), pages.css (páginas) y play.css (la partida)
js/engine.js      la puerta de la página hacia el motor de Python
js/worker.js      Pyodide en un hilo aparte
js/crew.js        alias, frases y recompensas de cada rival
js/marcador.js    la clasificación del torneo (descarga leaderboard.json y dibuja la tabla)
js/app.js         rutas, tema, sonido, cartel personal y tablón de rivales
js/play.js        la partida
img/              los retratos de los personajes (PNG con fondo transparente)
webglue.py        el puente entre JavaScript y el motor
```

Para añadir un personaje: pon su PNG con fondo transparente en `img/` y una entrada en `js/crew.js`
con el **nombre exacto** del bot (el que devuelve `get_name()`). Más en
[el diseño de la web](../docs/diseno-jugar.md).
