"""Tests del puente de la web (``web/webglue.py``), sin navegador.

El puente es la única puerta entre JavaScript y el motor, así que aquí se comprueba que
habla solo JSON, que sus respuestas coinciden con las del motor (no tiene reglas propias),
que rechaza las entradas malas con un mensaje claro y que un bot roto no rompe la partida.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
import webglue

from bots_rotos import BOTS_ROTOS
from reversibounty import (
    BLACK,
    WHITE,
    GameState,
    Move,
    Player,
    apply_move,
    flips,
    initial_state,
    is_terminal,
    legal_moves,
    play_game,
    score,
    winner,
)
from reversibounty.bots import RandomPlayer

PLAYERS_DIR = Path(__file__).resolve().parents[1] / "players"


def llamar(nombre: str, *args: object) -> dict:
    """Llama a una función del puente como lo hace la página: argumentos y respuesta en JSON."""
    respuesta = getattr(webglue, nombre)(*(json.dumps(a) for a in args))
    assert isinstance(respuesta, str), "el puente siempre devuelve texto JSON"
    return json.loads(respuesta)


def ok(nombre: str, *args: object):
    respuesta = llamar(nombre, *args)
    assert respuesta["ok"], respuesta.get("error")
    return respuesta["result"]


def error(nombre: str, *args: object) -> str:
    respuesta = llamar(nombre, *args)
    assert respuesta["ok"] is False
    assert isinstance(respuesta["error"], str) and respuesta["error"]
    return respuesta["error"]


@pytest.fixture(autouse=True)
def registro():
    """Cada test empieza con el registro real cargado y sin partida en curso."""
    ok("init", str(PLAYERS_DIR))
    yield


class PrimeraJugada(Player):
    """Juega siempre la primera jugada legal: hace de persona en los tests."""

    @classmethod
    def get_name(cls) -> str:
        return "primera"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Tests"]

    @classmethod
    def get_description(cls) -> str:
        return "Siempre la primera jugada legal."

    @classmethod
    def get_icon(cls) -> str:
        return "1️⃣"

    def choose_move(self, state: GameState) -> Move:
        return legal_moves(state)[0]


def con_bot(monkeypatch, cls: type[Player]) -> None:
    """Añade un bot al registro cargado, solo durante el test."""
    monkeypatch.setitem(webglue._JUGADORES, cls.get_name(), cls)


# -- Jugadores --------------------------------------------------------------- #


def test_init_devuelve_los_jugadores_del_registro():
    jugadores = ok("init", str(PLAYERS_DIR))
    aleatorio = next(j for j in jugadores if j["name"] == "Aleatorio")
    assert aleatorio == {
        "name": "Aleatorio",
        "icon": RandomPlayer.get_icon(),
        "authors": RandomPlayer.get_authors(),
        "description": RandomPlayer.get_description(),
    }


def test_players_devuelve_lo_mismo_que_init():
    assert ok("players") == ok("init", str(PLAYERS_DIR))


def test_la_lista_de_jugadores_sale_del_registro(tmp_path):
    """Un bot nuevo en players/ aparece en la web sin tocar el puente."""
    (tmp_path / "custom").mkdir()
    (tmp_path / "custom" / "players.yaml").write_text(
        "players:\n  - {module: reversibounty.bots.random_player, class: RandomPlayer}\n",
        encoding="utf-8",
    )
    assert [j["name"] for j in ok("init", str(tmp_path))] == ["Aleatorio"]


def test_un_registro_roto_da_un_error_claro(tmp_path):
    assert "registro de jugadores" in error("init", str(tmp_path))


def test_players_sin_init_da_un_error_claro(monkeypatch):
    monkeypatch.setattr(webglue, "_JUGADORES", {})
    assert "init" in error("players")


# -- Posiciones: el puente repite lo que dice el motor ---------------------- #


def test_new_game_describe_la_posicion_inicial():
    vista = ok("new_game")
    assert vista["state"] == initial_state().to_dict()
    assert vista["turn"] == BLACK
    assert vista["legal"] == [[2, 3], [3, 2], [4, 5], [5, 4]]
    assert vista["score"] == [2, 2]
    assert vista["over"] is False
    assert vista["winner"] is None and vista["forfeit"] is None


def posiciones_aleatorias(n: int = 40, semilla: int = 3) -> list[GameState]:
    rng = random.Random(semilla)
    posiciones, state = [], initial_state()
    while len(posiciones) < n:
        posiciones.append(state)
        state = initial_state() if is_terminal(state) else apply_move(state, rng.choice(legal_moves(state)))
    return posiciones


@pytest.mark.parametrize("state", posiciones_aleatorias(), ids=lambda s: f"{sum(score(s))}fichas")
def test_view_coincide_con_el_motor(state):
    vista = ok("view", state.to_dict())
    assert vista["legal"] == [list(m) for m in legal_moves(state)]
    assert ok("legal_moves", state.to_dict()) == vista["legal"]
    assert vista["score"] == list(score(state))
    assert vista["over"] == is_terminal(state)
    assert vista["winner"] == winner(state)
    assert vista["turn"] == (None if is_terminal(state) else state.player)


def test_play_move_aplica_la_jugada_con_el_motor():
    vista = ok("play_move", initial_state().to_dict(), [2, 3])
    assert vista["state"] == apply_move(initial_state(), (2, 3)).to_dict()
    assert vista["move"] == [2, 3] and vista["notation"] == "d3"
    assert vista["mover"] == BLACK
    assert vista["flipped"] == [[3, 3]]
    assert vista["turn"] == WHITE and vista["passed"] is False


def test_play_move_acepta_la_notacion():
    assert ok("play_move", initial_state().to_dict(), "d3") == ok(
        "play_move", initial_state().to_dict(), [2, 3]
    )


def test_play_move_avisa_cuando_el_rival_pasa():
    # Negras en a1 y a8, blancas en b1, b8 y c8. Tras c1 (voltea b1) las blancas solo
    # tienen fichas en la fila 8, y no pueden encerrar nada: pasan y vuelven a mover negras.
    tablero = [[0] * 8 for _ in range(8)]
    tablero[0][0], tablero[0][1] = BLACK, WHITE
    tablero[7][0], tablero[7][1], tablero[7][2] = BLACK, WHITE, WHITE
    vista = ok("play_move", {"board": tablero, "player": BLACK}, "c1")
    assert vista["passed"] is True
    assert vista["turn"] == BLACK
    assert vista["legal"] == [[7, 3]]


def test_la_partida_terminada_no_tiene_turno():
    jugadas = ["e6", "f4", "e3", "f6", "g5", "d6", "e7", "f5"]  # de docs/reglas.md
    state = initial_state().to_dict()
    for jugada in jugadas:
        state = ok("play_move", state, jugada)["state"]
    vista = ok("play_move", state, "c5")
    assert vista["over"] is True
    assert vista["turn"] is None and vista["legal"] == []
    assert vista["winner"] == BLACK and vista["score"] == [13, 0]
    assert vista["passed"] is False
    assert "terminado" in error("play_move", vista["state"], "a1")


# -- Entradas malas: siempre un mensaje claro, nunca una excepción ---------- #


@pytest.mark.parametrize(
    ("args", "mensaje"),
    [
        ((initial_state().to_dict(), [0, 0]), "ilegal"),
        ((initial_state().to_dict(), "d4"), "ilegal"),
        ((initial_state().to_dict(), "z9"), "no válida"),
        ((initial_state().to_dict(), [2]), "fila, columna"),
        ((initial_state().to_dict(), [2, True]), "fila, columna"),
        ((initial_state().to_dict(), None), "fila, columna"),
        (({"board": [[0] * 8] * 7, "player": 1}, "d3"), "8 filas"),
        (({"board": [[0] * 8] * 8, "player": 2}, "d3"), "player"),
        (([1, 2], "d3"), "objeto"),
        (("hola", "d3"), "objeto"),
        ((initial_state().to_dict(),), "espera 2 argumentos"),
    ],
)
def test_play_move_rechaza_entradas_malas(args, mensaje):
    assert mensaje in error("play_move", *args)


def test_un_argumento_que_no_es_json_da_un_error_claro():
    respuesta = json.loads(webglue.view("{esto no es json"))
    assert respuesta["ok"] is False and "no es JSON" in respuesta["error"]


def test_un_argumento_que_no_es_texto_da_un_error_claro():
    respuesta = json.loads(webglue.view({"board": []}))
    assert respuesta["ok"] is False and "texto JSON" in respuesta["error"]


@pytest.mark.parametrize(
    ("args", "mensaje"),
    [
        (("no-existe", WHITE, 1), "Aleatorio"),
        ((3, WHITE, 1), "ningún jugador"),
        (("Aleatorio", 0, 1), "bot_color"),
        (("Aleatorio", True, 1), "bot_color"),
        (("Aleatorio", WHITE, "1"), "seed"),
        (("Aleatorio", WHITE), "espera 3 argumentos"),
    ],
)
def test_start_game_rechaza_entradas_malas(args, mensaje):
    assert mensaje in error("start_game", *args)


def test_bot_move_sin_partida_da_un_error_claro():
    assert "start_game" in error("bot_move", initial_state().to_dict())


def test_bot_move_fuera_de_su_turno_da_un_error_claro():
    ok("start_game", "Aleatorio", WHITE, 1)
    assert "turno" in error("bot_move", initial_state().to_dict())  # mueven negras


def test_un_fallo_inesperado_tambien_vuelve_como_json(monkeypatch):
    def roto(*_):
        raise RuntimeError("se ha roto el motor")

    monkeypatch.setattr(webglue.game, "legal_moves", roto)
    assert "error interno" in error("new_game")


# -- El bot en el otro asiento ---------------------------------------------- #


def test_start_game_crea_el_bot_y_devuelve_su_identidad():
    partida = ok("start_game", "Aleatorio", WHITE, 5)
    assert partida["bot"]["name"] == "Aleatorio"
    assert partida["bot_color"] == WHITE


def test_bot_move_juega_una_jugada_legal():
    ok("start_game", "Aleatorio", BLACK, 5)
    vista = ok("bot_move", initial_state().to_dict())
    assert vista["move"] in [list(m) for m in legal_moves(initial_state())]
    assert vista["mover"] == BLACK and vista["turn"] == WHITE
    assert vista["forfeit"] is None


def test_con_la_misma_semilla_el_bot_repite_sus_jugadas():
    """Lo que hace la página al recargar: misma semilla, mismas decisiones."""
    ok("start_game", "Aleatorio", BLACK, 9)
    primera = ok("bot_move", initial_state().to_dict())["move"]
    ok("start_game", "Aleatorio", BLACK, 9)
    assert ok("bot_move", initial_state().to_dict())["move"] == primera


@pytest.mark.parametrize("roto", BOTS_ROTOS, ids=lambda cls: cls.__name__)
def test_un_bot_roto_pierde_y_la_partida_termina(monkeypatch, roto):
    con_bot(monkeypatch, roto)
    ok("start_game", roto.get_name(), BLACK, 1)
    vista = ok("bot_move", initial_state().to_dict())
    assert vista["over"] is True
    assert vista["winner"] == WHITE  # gana la persona
    assert vista["turn"] is None and vista["legal"] == []
    assert vista["forfeit"].startswith(roto.get_name())
    assert vista["state"] == initial_state().to_dict()  # el tablero no ha cambiado


def test_un_bot_que_no_se_puede_crear_da_un_error_claro(monkeypatch):
    class NoSeCrea(PrimeraJugada):
        @classmethod
        def get_name(cls) -> str:
            return "no-se-crea"

        @classmethod
        def create(cls, seed: int) -> Player:
            raise RuntimeError("sin memoria")

    con_bot(monkeypatch, NoSeCrea)
    assert "no se pudo crear" in error("start_game", "no-se-crea", WHITE, 1)


# -- Una partida entera, solo a través del puente --------------------------- #


@pytest.mark.parametrize("color_bot", [WHITE, BLACK], ids=["bot-blancas", "bot-negras"])
def test_una_partida_completa_a_traves_del_puente_es_la_de_play_game(color_bot):
    """La persona juega siempre su primera jugada legal y el bot es el aleatorio.

    Jugando solo con el puente, como la página, sale exactamente la misma partida que con
    :func:`play_game` y los mismos jugadores: el puente no añade ni cambia ninguna regla.
    """
    semilla = 2026
    ok("start_game", "Aleatorio", color_bot, semilla)
    vista = ok("new_game")
    jugadas = []
    while not vista["over"]:
        if vista["turn"] == color_bot:
            vista = ok("bot_move", vista["state"])
        else:
            vista = ok("play_move", vista["state"], vista["legal"][0])
        jugadas.append(tuple(vista["move"]))

    humano, bot = PrimeraJugada(), RandomPlayer.create(seed=semilla)
    negras, blancas = (bot, humano) if color_bot == BLACK else (humano, bot)
    esperado = play_game(negras, blancas)
    assert tuple(jugadas) == esperado.moves
    assert vista["score"] == list(esperado.score)
    assert vista["winner"] == esperado.winner
    assert vista["forfeit"] is None
    assert sum(vista["score"]) <= 64


def test_la_vista_ya_no_lleva_el_campo_duplicado_terminal():
    assert "terminal" not in ok("new_game")


def test_las_fichas_volteadas_son_las_que_calcula_el_motor():
    """El puente las deduce de comparar los tableros; deben coincidir con ``flips``."""
    for state in posiciones_aleatorias(60, semilla=11):
        if is_terminal(state):
            continue
        for jugada in legal_moves(state):
            respuesta = ok("play_move", state.to_dict(), list(jugada))
            esperadas = sorted(flips(state.board, state.player, jugada))
            assert sorted(map(tuple, respuesta["flipped"])) == esperadas
