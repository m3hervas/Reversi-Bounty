"""El tutorial de la web (Aprende jugando): cada lección se puede jugar de verdad con el motor.

Las lecciones son datos (web/data/tutorial.json). Si una pidiera una jugada ilegal o fuera de
turno, el jugador nuevo se quedaría atascado delante de una casilla que no responde: estos tests
reproducen cada lección con el mismo motor que usa la página y lo impiden antes de publicarla.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import webglue

from reversibounty.game import (
    BLACK,
    WHITE,
    GameState,
    apply_move,
    flips,
    legal_moves,
    score,
    str_to_move,
)

WEB = Path(__file__).resolve().parent.parent / "web"
DATOS = json.loads((WEB / "data" / "tutorial.json").read_text(encoding="utf-8"))
LECCIONES = DATOS["lessons"]
JS = (WEB / "js" / "tutorial.js").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")
PIEZA = {"X": BLACK, "O": WHITE, ".": 0}


def posicion(leccion: dict) -> GameState:
    """La posición de partida de una lección, en el formato del motor."""
    tablero = tuple(tuple(PIEZA[c] for c in fila) for fila in leccion["board"])
    return GameState(board=tablero, player=PIEZA[leccion["to_move"]])


def test_el_archivo_tiene_la_version_que_lee_la_pagina():
    assert DATOS["version"] == int(re.search(r"const VERSION = (\d+)", JS).group(1))
    assert LECCIONES, "no hay ninguna lección"
    ids = [leccion["id"] for leccion in LECCIONES]
    assert len(ids) == len(set(ids)), "hay dos lecciones con el mismo id"


@pytest.mark.parametrize("leccion", LECCIONES, ids=lambda leccion: leccion["id"])
def test_la_posicion_es_un_tablero_valido_y_empiezan_las_calaveras(leccion):
    assert len(leccion["board"]) == 8 and all(len(fila) == 8 for fila in leccion["board"])
    assert all(set(fila) <= set(PIEZA) for fila in leccion["board"]), "solo X, O y ."
    assert leccion["to_move"] == "X", "el jugador lleva las calaveras y empieza moviendo"
    assert legal_moves(posicion(leccion)), "en la posición inicial no hay ninguna jugada"


@pytest.mark.parametrize("leccion", LECCIONES, ids=lambda leccion: leccion["id"])
def test_el_guion_se_puede_jugar_entero_con_el_motor(leccion):
    """Cada jugada obligada es legal en su turno: tú con calaveras y el rival con sombreros."""
    assert leccion["kind"] == "guion"
    state = posicion(leccion)
    for numero, paso in enumerate(leccion["steps"], start=1):
        if paso["who"] == "volver":  # el tablero vuelve a la posición de partida
            assert numero > 1, "no se puede volver atrás antes de jugar nada"
            state = posicion(leccion)
            continue
        donde = f"{leccion['id']}, paso {numero} ({paso['move']})"
        assert paso["who"] in ("tu", "rival"), donde
        assert state.player == (BLACK if paso["who"] == "tu" else WHITE), f"{donde}: no es su turno"
        jugada = str_to_move(paso["move"])
        assert jugada in legal_moves(state), f"{donde}: no es una jugada legal"
        state = apply_move(state, jugada)
    assert any(paso["who"] == "tu" for paso in leccion["steps"]), "el jugador no juega nada"


@pytest.mark.parametrize("leccion", LECCIONES, ids=lambda leccion: leccion["id"])
def test_cada_momento_tiene_su_frase_del_mentor(leccion):
    textos = [leccion["title"], leccion["intro"], leccion["done"], *(p["say"] for p in leccion["steps"])]
    assert all(isinstance(t, str) and t.strip() for t in textos)


def test_la_leccion_1_es_la_apertura_del_tigre():
    primera = LECCIONES[0]
    assert posicion(primera) == webglue.game.initial_state()
    assert [p["move"] for p in primera["steps"]] == ["f5", "d6", "c3", "d3", "c4"]


def test_la_leccion_2_es_una_trampa_de_verdad():
    """g7 tienta (voltea más), regala la esquina h8 y hace perder; f1 no regala ninguna."""
    trampa = next(leccion for leccion in LECCIONES if leccion["id"] == "trampa")
    pasos = [(p["who"], p.get("move")) for p in trampa["steps"]]
    assert pasos == [
        ("tu", "g7"), ("rival", "h8"), ("volver", None),
        ("tu", "f1"), ("rival", "c2"), ("tu", "e6"), ("rival", "c1"), ("tu", "h6"),
    ]
    inicio = posicion(trampa)
    antes, _ = score(inicio)
    mala, buena, esquina = str_to_move("g7"), str_to_move("f1"), str_to_move("h8")

    assert inicio.board[esquina[0]][esquina[1]] == 0  # g7 es la casilla X de una esquina vacía
    assert len(flips(inicio.board, BLACK, mala)) > len(flips(inicio.board, BLACK, buena))
    tras_mala = apply_move(inicio, mala)
    castigo = apply_move(tras_mala, esquina)
    assert score(castigo)[0] < antes  # acabas con menos fichas que antes de mover

    tras_buena = apply_move(inicio, buena)
    esquinas = {str_to_move(e) for e in ("a1", "h1", "a8", "h8")}
    assert not esquinas & set(legal_moves(tras_buena))  # el rival no puede coger ninguna esquina
    peor = max(len(flips(tras_buena.board, WHITE, r)) for r in legal_moves(tras_buena))
    assert peor <= 2 and len(flips(tras_buena.board, WHITE, str_to_move("c2"))) == peor

    # Dos jugadas más de la línea buena: el rival nunca puede coger una esquina y el marcador
    # acaba 25 a 12, frente al 15 a 19 de la línea mala (lo que dice el mentor).
    s = tras_buena
    for jugada in ("c2", "e6", "c1", "h6"):
        s = apply_move(s, str_to_move(jugada))
        if s.player == WHITE:
            assert not esquinas & set(legal_moves(s)), f"tras {jugada} el rival puede coger una esquina"
    assert score(s) == (25, 12)
    assert score(castigo) == (15, 19)


def test_la_pagina_solo_pregunta_al_motor_y_no_calcula_reglas():
    llamadas = set(re.findall(r'RB\.engine\.call\("(\w+)"', JS))
    assert llamadas and llamadas <= set(webglue.__all__), llamadas - set(webglue.__all__)
    assert llamadas == {"view", "play_move"}  # validar la posición y aplicar cada jugada


def test_solo_se_puede_pulsar_la_casilla_obligada():
    # La marca de jugada (data-playable) depende solo de la casilla obligada, nunca de view.legal.
    assert "const playable = k === forced;" in JS
    assert "key(move) !== key(tut.forced)" in JS


def test_tras_la_jugada_del_rival_se_espera_al_jugador_para_seguir():
    # Sin esto la frase del rival desaparece antes de poder leerla.
    rival = JS[JS.index("// El rival juega y la partida se para"):JS.index("function onPick")]
    assert "await continuePressed(token);" in rival
    assert rival.index("await play(token, move)") < rival.index("await continuePressed(token);")
    assert '"Continuar ▸"' in JS


def test_la_bienvenida_solo_se_ve_antes_de_la_primera_jugada():
    jugar = JS[JS.index("async function play("):JS.index("function continuePressed")]
    assert '$("tut-intro").textContent = "";' in jugar


def test_el_mentor_tiene_su_cartel_de_se_busca_como_los_rivales():
    vista = re.search(r'<section class="view" data-view="aprende".*?</section>', HTML, re.S).group(0)
    cartel = re.search(r'<div class="wanted paper tut__poster".*?<div class="wanted__foot"', vista, re.S)
    assert cartel, "el mentor no tiene cartel"
    for parte in ("wanted__top", "wanted__pic", "wanted__sub", "wanted__name", "wanted__money", "luffy.png"):
        assert parte in cartel.group(0), parte


def test_el_texto_de_las_lecciones_entra_como_texto_y_nunca_como_html():
    for peligroso in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert peligroso not in JS, peligroso


def test_se_entra_con_el_boton_aprende_jugando_de_la_portada():
    portada = re.search(r'<section class="view" data-view="inicio".*?</section>', HTML, re.S).group(0)
    assert re.search(r'<a [^>]*href="#/aprende"[^>]*>Aprende jugando</a>', portada)
    assert 'data-route="aprende"' not in HTML  # no está en el menú de arriba


def test_cada_id_que_usa_el_tutorial_existe_en_el_html():
    ids = set(re.findall(r'\bid="([^"]+)"', HTML))
    usados = set(re.findall(r'\$\("([a-z-]+)"\)', JS))
    assert usados and usados <= ids, usados - ids
