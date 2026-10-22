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
