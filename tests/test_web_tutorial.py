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
GUIONES = [leccion for leccion in LECCIONES if leccion["kind"] == "guion"]
LIBRES = [leccion for leccion in LECCIONES if leccion["kind"] == "libre"]
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
    assert all(leccion["kind"] in ("guion", "libre") for leccion in LECCIONES)


@pytest.mark.parametrize("leccion", LECCIONES, ids=lambda leccion: leccion["id"])
def test_la_posicion_es_un_tablero_valido_y_empiezan_las_calaveras(leccion):
    assert len(leccion["board"]) == 8 and all(len(fila) == 8 for fila in leccion["board"])
    assert all(set(fila) <= set(PIEZA) for fila in leccion["board"]), "solo X, O y ."
    assert leccion["to_move"] == "X", "el jugador lleva las calaveras y empieza moviendo"
    assert legal_moves(posicion(leccion)), "en la posición inicial no hay ninguna jugada"


@pytest.mark.parametrize("leccion", GUIONES, ids=lambda leccion: leccion["id"])
def test_el_guion_se_puede_jugar_entero_con_el_motor(leccion):
    """Cada jugada obligada es legal en su turno: tú con calaveras y el rival con sombreros."""
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
    if leccion["kind"] == "guion":
        momentos = [leccion["done"], *(p["say"] for p in leccion["steps"])]
    else:
        momentos = [leccion["win"], leccion["lose"]]
    textos = [leccion["title"], leccion["intro"], *momentos]
    assert all(isinstance(t, str) and t.strip() for t in textos)


# -- La lección libre: una partida de verdad contra un bot del registro ---- #


@pytest.mark.parametrize("leccion", LIBRES, ids=lambda leccion: leccion["id"])
def test_el_rival_de_la_leccion_libre_esta_en_el_registro(leccion):
    from reversibounty.manifest import load_players

    assert leccion["rival"] in load_players(), f"no hay ningún bot llamado {leccion['rival']!r}"


def test_la_leccion_3_es_un_final_igualado_contra_el_bot_aleatorio():
    from reversibounty.bots import RandomPlayer
    from reversibounty.manifest import load_players

    final = next(leccion for leccion in LECCIONES if leccion["id"] == "final")
    assert final is LECCIONES[-1], "el final libre cierra el tutorial"
    calaveras, sombreros = score(posicion(final))
    assert calaveras == sombreros, "la posición empieza empatada"
    assert 13 <= 64 - calaveras - sombreros <= 16, "unas 15 casillas libres"
    assert issubclass(load_players()[final["rival"]], RandomPlayer)


def test_el_mentor_valora_cada_jugada_con_las_cifras_del_motor():
    """coach dice, para cada jugada, lo que voltea y lo peor que puede quitarte el rival después."""
    state = posicion(next(leccion for leccion in LECCIONES if leccion["kind"] == "libre"))
    respuesta = json.loads(webglue.coach(json.dumps(state.to_dict())))
    assert respuesta["ok"], respuesta
    consejos = respuesta["result"]
    assert [tuple(c["move"]) for c in consejos] == legal_moves(state)
    for consejo in consejos:
        jugada = tuple(consejo["move"])
        tras = apply_move(state, jugada)
        assert consejo["flips"] == len(flips(state.board, BLACK, jugada))
        respuestas = legal_moves(tras) if tras.player == WHITE else []
        peor = max((len(flips(tras.board, WHITE, r)) for r in respuestas), default=0)
        assert consejo["risk"] == peor, consejo
        if consejo["reply"]:
            assert len(flips(tras.board, WHITE, str_to_move(consejo["reply"]))) == peor


def test_si_el_rival_no_puede_responder_el_riesgo_es_cero():
    # Un sombrero en a1 y una calavera en b1, y mueven los sombreros: tras c1 las calaveras se quedan
    # sin fichas, la partida termina y nadie puede quitarte nada.
    tablero = [[0] * 8 for _ in range(8)]
    tablero[0][0], tablero[0][1] = WHITE, BLACK
    state = GameState(board=tuple(map(tuple, tablero)), player=WHITE)
    consejos = json.loads(webglue.coach(json.dumps(state.to_dict())))["result"]
    assert consejos == [{"move": [0, 2], "notation": "c1", "flips": 1, "risk": 0, "reply": None}]


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
    # validar la posición, aplicar jugadas y, en la lección libre, el rival y la valoración del mentor
    assert llamadas == {"view", "play_move", "start_match", "bot_move", "coach"}


def test_solo_se_puede_pulsar_la_casilla_obligada():
    # Solo responden las casillas de tut.allowed: en un guion, una sola (la obligada); todas las
    # legales solo en la lección libre.
    assert "const playable = allowed.has(k);" in JS
    assert "!tut.allowed.has(key(move))" in JS
    guion = JS[JS.index("async function next("):JS.index("async function rewind(")]
    assert "tut.allowed = new Set([key(move)]);" in guion and "view.legal" not in guion.split("say(step.say")[1]
    libre = JS[JS.index("async function freeTurn("):JS.index("function advise(")]
    assert "tut.allowed = new Set(view.legal.map(key));" in libre


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


def test_al_entrar_siempre_se_empieza_por_la_leccion_1():
    # Aunque el navegador recuerde lecciones superadas: se ven marcadas, pero se empieza por la 1.
    entrar = JS[JS.index("async function enter("):JS.index("RB.tutorial = {")]
    assert entrar.count("startLesson(0)") == 2  # al volver a entrar y al terminar la primera carga
    assert "startLesson(Math.min" not in entrar


def test_la_bienvenida_sale_solo_antes_de_la_leccion_1():
    empezar = JS[JS.index("async function startLesson("):JS.index("function welcome(")]
    assert "if (i === 0 && !(await welcome(token))) return;" in empezar
    vista = re.search(r'<section class="view" data-view="aprende".*?</section>', HTML, re.S).group(0)
    bienvenida = re.search(r'<div class="overlay tut__welcome" id="tut-welcome" hidden>.*?¡Zarpamos!', vista, re.S)
    assert bienvenida, "falta la pantalla de bienvenida, oculta hasta que la abre el tutorial"
    # La lista sale de las lecciones (sus títulos), no se escribe a mano en el HTML.
    assert 'id="tut-welcome-list"></ol>' in vista and "lesson.title" in JS[JS.index("function welcome("):]


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
