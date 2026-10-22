"""Empaqueta el código de Python que necesita la web en ``web/py.zip``.

La web ejecuta en el navegador el mismo paquete que usan los tests y el torneo. El
navegador no puede leer el repositorio, así que este script reúne en un zip todo lo que
importa la página:

* ``reversibounty/``: el paquete, copiado de ``src/reversibounty``.
* ``players/``: el registro de jugadores (las dos listas y los bots enviados).
* ``webglue.py``: el puente entre JavaScript y el motor.

El worker de la web descarga el zip, lo descomprime con Pyodide y añade la carpeta al
``sys.path``: dentro quedan ``reversibounty``, ``players`` y ``webglue`` uno junto a otro.

Decisiones de diseño:

* ``web/py.zip`` no se sube al repositorio (está en ``.gitignore``). Es un archivo
  generado: si se subiera, cada cambio del motor aparecería dos veces en la revisión.
* El zip es reproducible: los archivos van ordenados y con una fecha fija, así que el
  mismo código produce exactamente los mismos bytes.
* Solo entra código fuente: nada de ``__pycache__`` ni ``.pyc``, que dependen de la versión
  de Python de quien construye y no de la del navegador.

Uso::

    python scripts/build_web.py              # crea web/py.zip
    python scripts/build_web.py --out otro.zip
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "web" / "py.zip"

#: Fecha fija de todos los archivos del zip (la mínima que admite el formato).
_FECHA = (1980, 1, 1, 0, 0, 0)
_IGNORAR = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def _archivos(carpeta: Path) -> Iterator[Path]:
    """Los archivos de ``carpeta``, en orden, sin cachés ni bytecode."""
    for ruta in sorted(carpeta.rglob("*")):
        if ruta.is_file() and not _IGNORAR & set(ruta.parts) and ruta.suffix != ".pyc":
            yield ruta


def contenido(raiz: Path = RAIZ) -> list[tuple[Path, str]]:
    """Qué entra en el zip: parejas ``(archivo en disco, nombre dentro del zip)``.

    Args:
        raiz: la raíz del repositorio.

    Returns:
        Las parejas, ordenadas por su nombre dentro del zip.
    """
    paquete = raiz / "src" / "reversibounty"
    jugadores = raiz / "players"
    puente = raiz / "web" / "webglue.py"
    for necesario in (paquete, jugadores, puente):
        if not necesario.exists():
            raise FileNotFoundError(f"falta {necesario}")
    parejas = [(ruta, ruta.relative_to(paquete.parent).as_posix()) for ruta in _archivos(paquete)]
    parejas += [(ruta, ruta.relative_to(raiz).as_posix()) for ruta in _archivos(jugadores)]
    parejas.append((puente, "webglue.py"))
    return sorted(parejas, key=lambda pareja: pareja[1])


def build(destino: Path = DESTINO, raiz: Path = RAIZ) -> Path:
    """Crea el zip de la web.

    Args:
        destino: dónde escribir el zip. Por defecto, ``web/py.zip``.
        raiz: la raíz del repositorio.

    Returns:
        La ruta del zip creado.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for ruta, nombre in contenido(raiz):
            info = zipfile.ZipInfo(nombre, date_time=_FECHA)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16  # permisos normales de lectura
            zf.writestr(info, ruta.read_bytes())
    return destino


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Empaqueta el código de la web en un zip.")
    parser.add_argument("--out", type=Path, default=DESTINO, help="ruta del zip (web/py.zip)")
    args = parser.parse_args(argv)
    destino = build(args.out)
    with zipfile.ZipFile(destino) as zf:
        total = len(zf.namelist())
    print(f"{destino} ({destino.stat().st_size / 1024:.1f} KB, {total} archivos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
