"""Genera el libro de aperturas de Zeff minimax: ``src/reversibounty/bots/zeff_libro.py``.

Recorre todas las posiciones que pueden aparecer en las primeras jugadas de una partida y, para
cada una, deja que Zeff piense mucho más de lo que puede pensar en una partida (``--segundos``
por posición en lugar de 0,5 s). Guarda la jugada que elige. En la partida, Zeff juega esas
posiciones al instante y con el análisis largo.

Las 8 simetrías del tablero no cambian el juego, así que solo se analiza una posición de cada
familia de posiciones simétricas (la canónica).

Uso::

    python scripts/generar_libro_zeff.py                  # 4 jugadas, 4 s por posición
    python scripts/generar_libro_zeff.py --jugadas 3 --segundos 2
"""

from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

from reversibounty import apply_move, initial_state, legal_moves
from reversibounty.bots.zeff_minmax import ZeffMinmaxPlayer, _bits, canonical

DESTINO = Path(__file__).resolve().parents[1] / "src" / "reversibounty" / "bots" / "zeff_libro.py"

CABECERA = '''"""Libro de aperturas de Zeff minimax. ARCHIVO GENERADO: no lo edites a mano.

Lo crea ``python scripts/generar_libro_zeff.py --jugadas {jugadas} --segundos {segundos:g}``.
Cada entrada es ``(fichas de quien mueve, fichas del rival) -> casilla``, con la posición en su
forma canónica (ver ``canonical`` en ``zeff_minmax.py``) y la casilla de 0 a 63 (fila * 8 +
columna). {n} posiciones.
"""

LIBRO: dict[tuple[int, int], int] = {{
'''


def posiciones(jugadas: int) -> list:
    """Una posición de cada familia simétrica, de las que salen en las primeras ``jugadas``."""
    vistas: dict[tuple[int, int], object] = {}
    nivel = [initial_state()]
    for _ in range(jugadas + 1):
        siguiente = []
        for estado in nivel:
            clave, _ = canonical(*_bits(estado))
            if clave in vistas:
                continue
            vistas[clave] = estado
            siguiente += [apply_move(estado, m) for m in legal_moves(estado)]
        nivel = siguiente
    return [e for e in vistas.values() if len(legal_moves(e)) > 1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera el libro de aperturas de Zeff.")
    parser.add_argument("--jugadas", type=int, default=4, help="jugadas ya hechas, como mucho")
    parser.add_argument("--segundos", type=float, default=4.0, help="tiempo de análisis por posición")
    args = parser.parse_args()

    todas = posiciones(args.jugadas)
    print(f"{len(todas)} posiciones distintas; unos {len(todas) * args.segundos / 60:.0f} min")
    libro: dict[tuple[int, int], int] = {}
    inicio = time.time()
    for numero, estado in enumerate(todas, 1):
        zeff = ZeffMinmaxPlayer(random.Random(0), time_limit=args.segundos, use_book=False)
        fila, columna = zeff.choose_move(estado)
        clave, mapa = canonical(*_bits(estado))
        libro[clave] = mapa[fila * 8 + columna]
        print(f"  {numero:>3}/{len(todas)}  profundidad {zeff.last_search.get('profundidad')}")

    lineas = [CABECERA.format(jugadas=args.jugadas, segundos=args.segundos, n=len(libro))]
    lineas += [f"    ({p}, {o}): {casilla},\n" for (p, o), casilla in sorted(libro.items())]
    lineas.append("}\n")
    DESTINO.write_text("".join(lineas), encoding="utf-8")
    print(f"Libro guardado en {DESTINO} ({time.time() - inicio:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
