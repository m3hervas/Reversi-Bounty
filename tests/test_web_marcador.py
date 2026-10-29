"""El marcador de la web (paso 5.5): lee el leaderboard.json que produce el torneo, sin jugar nada."""

from __future__ import annotations

import re
from pathlib import Path

from reversibounty.bots import GreedyPlayer, RandomPlayer
from reversibounty.tournament import run_tournament, write_leaderboard

WEB = Path(__file__).resolve().parent.parent / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
JS = (WEB / "js" / "marcador.js").read_text(encoding="utf-8")


def test_la_descarga_usa_no_cache_y_el_archivo_que_copia_pages():
    # Sin no-cache el navegador puede enseñar la clasificación del día anterior sin avisar.
    assert 'fetch(FILE, { cache: "no-cache" })' in JS
    assert 'FILE = "leaderboard.json"' in JS
    pages = (WEB.parent / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "web/leaderboard.json" in pages


def test_si_el_archivo_no_existe_la_pagina_lo_dice_en_vez_de_fallar():
    assert "response.status === 404" in JS
    assert "Todavía no hay clasificación" in JS
    assert ".catch(" in JS  # un fallo de red tampoco rompe la página


def test_el_marcador_no_inyecta_html_con_datos_ajenos():
    # Los nombres y los motivos de infracción los escriben los bots.
    assert "innerHTML" not in JS and "insertAdjacentHTML" not in JS


def test_el_marcador_no_juega_partidas():
    assert "engine.call" not in JS


def test_cada_id_que_usa_el_marcador_existe_en_el_html():
    ids = set(re.findall(r'\bid="([^"]+)"', HTML))
    usados = set(re.findall(r'\$\("([a-z-]+)"\)', JS))
    assert usados and usados <= ids, usados - ids


def test_el_marcador_lee_solo_campos_que_el_torneo_escribe(tmp_path):
    """Si el torneo renombra un campo, este test avisa antes de que la tabla salga vacía."""
    resultado = run_tournament(
        {RandomPlayer.get_name(): RandomPlayer, GreedyPlayer.get_name(): GreedyPlayer}, rounds=1, time_limit=1.0
    )
    import json

    datos = json.loads(write_leaderboard(resultado, tmp_path / "leaderboard.json").read_text(encoding="utf-8"))
    leidos_de_la_raiz = {"schema_version", "finished_at", "rounds", "seed", "standings"}
    assert leidos_de_la_raiz <= set(datos)
    campos = set(re.findall(r"entry\.([a-z_]+)|\bs\.([a-z_]+)", JS))
    campos = {a or b for a, b in campos} - {"rank"}  # «rank» lo pone la página si falta
    assert campos <= set(datos["standings"][0]), campos - set(datos["standings"][0])


def test_la_version_del_archivo_que_lee_es_la_que_escribe_el_torneo():
    from reversibounty.tournament import SCHEMA_VERSION

    assert f"SCHEMA = {SCHEMA_VERSION}" in JS


def test_el_apartado_esta_en_el_menu_y_en_la_cabecera():
    assert 'data-route="marcador"' in HTML
    assert '"marcador", "anadir"' in HTML.split("</script>")[0]
