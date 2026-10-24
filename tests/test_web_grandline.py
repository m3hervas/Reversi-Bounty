"""La web «Grand Line»: lo que une el HTML, el JavaScript y el motor tiene que cuadrar.

Una web estática no avisa de un id que falta ni de una función de Python que ya no existe: se queda
en blanco. Estos tests lo comprueban leyendo los archivos, sin navegador.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

from reversibounty.manifest import load_players

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
JS = {p.name: p.read_text(encoding="utf-8") for p in (WEB / "js").glob("*.js")}
PROPIOS = ("app.js", "crew.js", "play.js")  # engine.js y worker.js son el puente al motor


def _ids_html() -> set[str]:
    return set(re.findall(r'\bid="([^"]+)"', HTML))


# ------------------------------------------------------------------ el motor --- #


def test_cada_funcion_de_python_que_llama_la_web_esta_declarada_en_el_puente():
    spec = importlib.util.spec_from_file_location("webglue", WEB / "webglue.py")
    assert spec is not None and spec.loader is not None
    webglue = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(webglue)
    llamadas: set[str] = set()
    for nombre in PROPIOS:
        llamadas |= set(re.findall(r'engine\.call\(\s*"([a-z_]+)"', JS[nombre]))
    assert llamadas, "la web no llama al motor"
    assert llamadas <= set(webglue.__all__), llamadas - set(webglue.__all__)


def test_la_web_no_reimplementa_las_reglas_del_reversi():
    """Jugadas legales, volteos y final salen de Python: en JS no hay ninguna de esas funciones."""
    for nombre in PROPIOS:
        for palabra in ("legalMoves", "applyMove", "isTerminal", "flipDirection"):
            assert palabra not in JS[nombre], f"{nombre} parece implementar reglas ({palabra})"


# ----------------------------------------------------------------- los ids --- #


def test_los_ids_que_busca_el_javascript_existen_en_el_html():
    ids = _ids_html()
    for nombre in PROPIOS:
        buscados = set(re.findall(r'\$\("([A-Za-z0-9_-]+)"\)', JS[nombre]))
        buscados |= set(re.findall(r'getElementById\("([A-Za-z0-9_-]+)"\)', JS[nombre]))
        assert buscados - ids == set(), f"{nombre} busca ids que no existen: {buscados - ids}"


@pytest.mark.parametrize("color", ["1", "-1"])
def test_cada_bando_tiene_su_cartel_su_selector_y_su_marcador(color):
    ids = _ids_html()
    for plantilla in (
        "seat-{c}", "pcol-{c}", "rcard-{c}", "say-{c}", "cc-{c}", "cn-{c}", "cs-{c}",
        "pp-{c}-pic", "pp-{c}-aka", "pp-{c}-name", "pp-{c}-bounty", "pp-{c}-foot",
    ):
        assert plantilla.format(c=color) in ids, plantilla.format(c=color)


def test_el_selector_de_jugadores_esta_encima_de_cada_cartel_y_el_boton_junto_al_marcador():
    for color in ("1", "-1"):
        columna = re.search(rf'<aside class="poster-col" id="pcol-{color}".*?</aside>', HTML, re.S)
        assert columna is not None
        assert f'id="seat-{color}"' in columna.group(0)
        assert columna.group(0).index('class="pick"') < columna.group(0).index('class="rcard"')
    marcador = re.search(r'<div class="panel scorebar">.*?<div class="meter"', HTML, re.S)
    assert marcador is not None and 'id="again"' in marcador.group(0)


def test_no_hay_atributos_id_repetidos():
    ids = re.findall(r'\bid="([^"]+)"', HTML)
    assert not {i for i in ids if ids.count(i) > 1}


# --------------------------------------------------------------- los rivales --- #


def test_cada_imagen_de_personaje_existe_y_tiene_fondo_transparente():
    rutas = set(re.findall(r'img:\s*"(img/[a-z0-9_]+\.png)', JS["crew.js"]))
    assert {"img/luffy.png", "img/zeff.png", "img/mr2.png", "img/wapol.png"} <= rutas
    for ruta in rutas:
        datos = (WEB / ruta).read_bytes()
        assert datos[:8] == b"\x89PNG\r\n\x1a\n", ruta
        assert datos[25] in (4, 6), f"{ruta} no tiene canal alfa (fondo transparente)"


def test_cada_personalidad_pertenece_a_un_bot_del_registro():
    """Una personalidad sin bot es código muerto; un bot sin personalidad recibe un cartel genérico."""
    nombres = set(load_players(RAIZ / "players"))
    personas = set(re.findall(r'^\s{4}"([^"]+)": \{\s*$', JS["crew.js"], re.M))
    assert personas, "no se ha encontrado ninguna personalidad en crew.js"
    assert personas <= nombres, personas - nombres


def test_los_carteles_no_muestran_quien_subio_cada_bot():
    """Los bots son independientes de sus autores: la web no enseña `authors` en ningún cartel."""
    for nombre in PROPIOS:
        assert "authors" not in JS[nombre], f"{nombre} usa los autores del bot"
    assert "Capitán(es)" not in HTML


# ---------------------------------------------------------------- las reglas --- #


def test_los_tableros_de_ejemplo_son_de_8_por_8_con_simbolos_validos():
    ejemplos = re.findall(r'data-mini="([^"]+)"', HTML)
    assert len(ejemplos) >= 6
    for ejemplo in ejemplos:
        filas = ejemplo.split("|")
        assert len(filas) == 8, ejemplo
        for fila in filas:
            assert re.fullmatch(r"[.hstSHKXCE]{8}", fila), fila


def test_las_cuatro_leyes_comparten_la_misma_tarjeta():
    leyes = re.findall(r'<article class="(law[^"]*)"', HTML)
    assert len(leyes) == 4 and len(set(leyes)) == 1, leyes


# ------------------------------------------------------------------ seguridad --- #


def test_el_javascript_propio_no_inyecta_html():
    for nombre in PROPIOS:
        assert "innerHTML" not in JS[nombre], f"{nombre} usa innerHTML"
        assert "insertAdjacentHTML" not in JS[nombre], f"{nombre} usa insertAdjacentHTML"
