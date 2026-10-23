"""La portada precalculada (``web/data/portada.json``) coincide con lo que calcula el motor.

La web la pinta al instante, antes de que Python arranque en el navegador. Si alguien cambia el
motor y no vuelve a ejecutar ``scripts/generar_portada.py``, este test avisa.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _generador():
    spec = importlib.util.spec_from_file_location("generar_portada", RAIZ / "scripts" / "generar_portada.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_archivo_de_la_portada_esta_al_dia():
    guardado = json.loads((RAIZ / "web" / "data" / "portada.json").read_text(encoding="utf-8"))
    assert guardado == _generador().construir(), "ejecuta: python scripts/generar_portada.py"


def test_la_apertura_son_cinco_jugadas_y_la_posicion_inicial_es_la_de_salida():
    datos = json.loads((RAIZ / "web" / "data" / "portada.json").read_text(encoding="utf-8"))
    assert len(datos["apertura"]["jugadas"]) == 5
    assert datos["inicio"]["score"] == [2, 2]
    assert datos["inicio"]["turn"] == 1
