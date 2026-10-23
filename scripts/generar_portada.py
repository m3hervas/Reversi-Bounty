"""Precalcula con el motor las posiciones que la web enseña antes de que Python arranque.

Pyodide tarda unos segundos en descargarse y arrancar. Para que la portada no se vea vacía
mientras tanto, la web pinta al instante dos posiciones ya calculadas: la de salida y una
apertura. No las calcula JavaScript (la web no tiene reglas): las calcula este script con el
mismo puente que usa el navegador, y ``tests/test_portada.py`` comprueba que el archivo no
se ha quedado viejo.

Uso::

    python scripts/generar_portada.py        # reescribe web/data/portada.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "web" / "data" / "portada.json"

#: La apertura que enseña la portada, una jugada por turno desde la posición inicial.
APERTURA = ["f5", "d6", "c3", "d3", "c4"]


def construir() -> dict[str, Any]:
    """Las posiciones de la portada, tal y como las devuelve el puente de la web."""
    sys.path.insert(0, str(RAIZ / "web"))
    import webglue  # noqa: PLC0415 - vive en web/, que no es un paquete instalado

    def leer(texto: str) -> Any:
        respuesta = json.loads(texto)
        assert respuesta["ok"], respuesta
        return respuesta["result"]

    vista = leer(webglue.new_game())
    inicio = vista
    for jugada in APERTURA:
        vista = leer(webglue.play_move(json.dumps(vista["state"]), json.dumps(jugada)))
    return {"inicio": inicio, "apertura": {"jugadas": APERTURA, "vista": vista}}


def main() -> int:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(construir(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{DESTINO} escrito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
