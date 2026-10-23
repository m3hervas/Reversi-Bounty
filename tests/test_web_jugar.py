"""La pestaña Jugar: el escenario, el avatar y sus animaciones cuadran entre HTML, CSS y JS.

Una web estática no avisa si un id cambia de nombre o si un estado de ánimo no tiene dibujo: el
personaje se queda mudo o sin cara. Estos tests lo comprueban leyendo los archivos, sin navegador.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parent.parent / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
STAGE_JS = (WEB / "js" / "stage.js").read_text(encoding="utf-8")
AVATARS_JS = (WEB / "js" / "avatars.js").read_text(encoding="utf-8")
PLAY_JS = (WEB / "js" / "play.js").read_text(encoding="utf-8")
AVATAR_CSS = (WEB / "css" / "avatar.css").read_text(encoding="utf-8")
JUGAR_CSS = (WEB / "css" / "jugar.css").read_text(encoding="utf-8")

#: Las partes del dibujo que animan los estilos: todo avatar debe traerlas.
PARTES_DEL_DIBUJO = [
    "av__body", "av__head", "av__hair-back", "av__iris", "av__eyes", "av__eyes-happy", "av__lids",
    "av__brow--l", "av__brow--r", "m-closed", "m-grin", "m-o", "m-sad", "av__spark", "av__tear",
]
ANIMOS = ["neutral", "think", "happy", "surprised", "sad"]


# -- El HTML ---------------------------------------------------------------- #


@pytest.mark.parametrize("ident", [
    "stage", "avatar", "bubble", "bubble-text", "board", "reach", "toast", "result", "status",
    "plate-1", "plate--1", "avatar-1", "avatar--1", "avatar-name", "play-rival",
])
def test_el_html_tiene_los_elementos_que_usa_el_escenario(ident):
    assert f'id="{ident}"' in HTML, ident


def test_el_tablero_esta_dentro_de_un_contenedor_inclinado_y_los_avisos_fuera_de_el():
    tablero = HTML[HTML.index('class="stage__board"'):]
    tablero = tablero[:tablero.index('<div class="reach"')]
    inclinado = tablero[tablero.index('class="board-tilt"'):tablero.index('id="toast"')]
    assert 'id="board"' in inclinado
    # Los avisos y el resultado no se inclinan con el tablero: flotan por encima.
    assert 'id="toast"' in tablero and 'id="result"' in tablero
    assert 'id="toast"' not in inclinado and 'id="result"' not in inclinado


def test_el_decorado_no_se_lee_en_voz_alta():
    for clase in ("stage__bg", "stage__spot", "stage__avatar", "stage__bubble", "stage__table"):
        fragmento = re.search(rf'<div class="{clase}"[^>]*>', HTML)
        assert fragmento and 'aria-hidden="true"' in fragmento.group(0), clase


# -- La disposición ---------------------------------------------------------- #


def test_el_escenario_ocupa_dos_tercios_como_minimo():
    assert re.search(r"grid-template-columns:\s*minmax\(260px,\s*1fr\)\s*minmax\(0,\s*2fr\)", JUGAR_CSS)


def test_el_tablero_esta_inclinado():
    assert re.search(r"transform:\s*rotateX\(\d+deg\)", JUGAR_CSS)
    assert "perspective:" in JUGAR_CSS


def test_el_escenario_es_oscuro_en_los_dos_temas():
    escenario = JUGAR_CSS[JUGAR_CSS.index(".stage {"):]
    escenario = escenario[:escenario.index("}")]
    assert "--ink: #f4f1e8" in escenario and "--on-ink: #121210" in escenario


# -- El avatar ----------------------------------------------------------------- #


def test_el_registro_tiene_a_mr_2_y_es_el_de_por_defecto():
    assert 'id: "mr2"' in AVATARS_JS and 'name: "Mr. 2"' in AVATARS_JS
    assert re.search(r"forBot\(\)\s*\{\s*return registry\.mr2", AVATARS_JS)


@pytest.mark.parametrize("parte", PARTES_DEL_DIBUJO)
def test_el_dibujo_de_mr_2_trae_cada_parte_que_anima_el_css(parte):
    assert parte in AVATARS_JS.split("const MR2 = {")[0], parte


def test_el_dibujo_usa_el_viewbox_que_espera_el_escenario():
    assert 'viewBox="0 0 400 480"' in AVATARS_JS
    assert re.search(r"VIEWBOX\s*=\s*\[400,\s*480\]", STAGE_JS)


@pytest.mark.parametrize("animo", [a for a in ANIMOS if a != "neutral"])
def test_cada_animo_tiene_su_cara_dibujada_en_el_css(animo):
    assert f'data-mood="{animo}"' in AVATAR_CSS


def test_todo_animo_que_pide_el_escenario_existe():
    usados = set(re.findall(r'setMood\("(\w+)"', STAGE_JS)) | set(re.findall(r'state\.base = "(\w+)"', STAGE_JS))
    assert usados <= set(ANIMOS), usados - set(ANIMOS)


def test_el_avatar_tiene_frases_para_todo_lo_que_dice_el_escenario():
    bloque = AVATARS_JS[AVATARS_JS.index("lines: {"):AVATARS_JS.index("RB.avatars = {")]
    listas = dict(re.findall(r"^\s+(\w+): \[(.*?)\],?$", bloque, re.MULTILINE))
    dichas = set(re.findall(r'say\("(\w+)"', STAGE_JS))
    dichas |= {"win", "lose", "draw"}  # finish() las elige con un ternario
    dichas |= {"pass", "youPass"}      # passed() también
    assert dichas <= set(listas), dichas - set(listas)
    for clave, frases in listas.items():
        assert re.findall(r'"[^"]+"', frases), f"«{clave}» no tiene ninguna frase"


# -- El movimiento ------------------------------------------------------------- #


def test_el_brazo_solo_anima_transform():
    """Regla de movimiento: nada de width, height, left o top en las animaciones del brazo."""
    llamadas = re.findall(r"\.animate\(\[(.*?)\],", STAGE_JS, re.DOTALL)
    assert llamadas
    for fotogramas in llamadas:
        claves = set(re.findall(r"\b(\w+):", fotogramas))
        assert claves == {"transform"}, claves


def test_el_brazo_dura_menos_de_300_ms_en_salir_y_usa_las_curvas_del_proyecto():
    assert re.search(r"REACH_MS\s*=\s*(\d+)", STAGE_JS) and int(re.search(r"REACH_MS\s*=\s*(\d+)", STAGE_JS).group(1)) <= 300
    assert "cubic-bezier(0.23, 1, 0.32, 1)" in STAGE_JS
    assert "cubic-bezier(0.77, 0, 0.175, 1)" in STAGE_JS


def test_con_reducir_movimiento_el_brazo_no_se_estira():
    assert "prefers-reduced-motion: reduce" in STAGE_JS
    assert re.search(r"reduceMotion\.matches", STAGE_JS)


def test_los_ojos_solo_siguen_al_raton_si_hay_raton():
    assert "(hover: hover) and (pointer: fine)" in STAGE_JS


def test_los_bucles_del_avatar_solo_mueven_transform_u_opacity():
    for nombre in re.findall(r"@keyframes (av-[\w-]+)", AVATAR_CSS):
        cuerpo = re.search(rf"@keyframes {nombre} \{{(.*)\n", AVATAR_CSS).group(1)
        propiedades = set(re.findall(r"(\w[\w-]*)\s*:", cuerpo))
        assert propiedades <= {"transform", "opacity"}, (nombre, propiedades)


# -- La relación con la partida ------------------------------------------------ #


def test_play_js_solo_toca_el_escenario_a_traves_de_act():
    """Si el escenario falla o falta, la partida sigue: ninguna llamada directa fuera de act()."""
    fuera = PLAY_JS.replace(PLAY_JS[PLAY_JS.index("function act("):PLAY_JS.index("/* Un efecto de sonido")], "")
    assert "RB.stage" not in fuera.replace("RB.stage.init", "")


def test_ningun_archivo_del_escenario_inyecta_html():
    for texto in (STAGE_JS, AVATARS_JS):
        assert "innerHTML" not in texto and "insertAdjacentHTML" not in texto
    assert "DOMParser" in STAGE_JS  # el dibujo se interpreta como SVG, no como HTML


def test_la_pagina_carga_los_archivos_del_escenario_en_orden():
    orden = [HTML.index(f'src="js/{n}.js') for n in ("avatars", "stage", "play")]
    assert orden == sorted(orden)
    assert "css/jugar.css" in HTML and "css/avatar.css" in HTML
