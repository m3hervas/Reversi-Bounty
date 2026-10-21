"""Tests del ejecutor de partidas: juega, valida cada jugada y no se rompe por un bot malo."""

from __future__ import annotations

import io
import random
from contextlib import redirect_stdout

from reversibounty import (
    BLACK,
    WHITE,
    GameResult,
    GameState,
    Move,
    apply_move,
    initial_state,
    is_terminal,
    legal_moves,
    play_game,
    score,
    winner,
)
from reversibounty.bots import RandomPlayer


class Primero:
    """Elige siempre la primera jugada legal. Guarda lo que recibe para poder inspeccionarlo."""

    def __init__(self) -> None:
        self.recibidos: list[GameState] = []

    def choose_move(self, state: GameState) -> Move:
        self.recibidos.append(state)
        return legal_moves(state)[0]


class Falla:
    """Un bot roto a propósito: ``jugada`` es lo que devuelve, o ``error`` lo que lanza."""

    def __init__(self, jugada: object = None, error: Exception | None = None) -> None:
        self.jugada = jugada
        self.error = error

    def choose_move(self, state: GameState):
        if self.error is not None:
            raise self.error
        return self.jugada


def reproducir(jugadas: tuple[Move, ...], inicio: GameState | None = None) -> GameState:
    """Reconstruye la posición final aplicando las jugadas desde ``inicio`` (o la inicial)."""
    state = initial_state() if inicio is None else inicio
    for jugada in jugadas:
        state = apply_move(state, jugada)
    return state


# -- Partida normal -------------------------------------------------------- #


def test_dos_jugadores_juegan_hasta_el_final():
    resultado = play_game(RandomPlayer.create(1), RandomPlayer.create(2))
    final = reproducir(resultado.moves)
    assert is_terminal(final)
    assert resultado.forfeit is None
    assert resultado.winner == winner(final)
    assert resultado.score == score(final)


def test_el_resultado_es_un_gameresult_con_el_historial():
    resultado = play_game(Primero(), Primero())
    assert isinstance(resultado, GameResult)
    assert resultado.moves
    assert all(isinstance(m, tuple) and len(m) == 2 for m in resultado.moves)


def test_misma_semilla_misma_partida():
    a = play_game(RandomPlayer.create(7), RandomPlayer.create(8))
    b = play_game(RandomPlayer.create(7), RandomPlayer.create(8))
    assert a == b


def test_partidas_con_pasos_de_turno_terminan_bien():
    # Con bots aleatorios, algunas partidas incluyen pasos: el ejecutor no debe atascarse.
    for semilla in range(40):
        resultado = play_game(RandomPlayer.create(semilla), RandomPlayer.create(semilla + 500))
        final = reproducir(resultado.moves)
        assert is_terminal(final)
        assert sum(resultado.score) <= 64


def test_gana_quien_tiene_mas_fichas():
    resultado = play_game(RandomPlayer.create(3), RandomPlayer.create(4))
    negras, blancas = resultado.score
    esperado = BLACK if negras > blancas else WHITE if blancas > negras else 0
    assert resultado.winner == esperado


# -- Turnos y colores ------------------------------------------------------ #


def test_player_a_juega_con_negras_y_player_b_con_blancas():
    a, b = Primero(), Primero()
    play_game(a, b)
    assert a.recibidos[0].player == BLACK
    assert b.recibidos[0].player == WHITE
    assert all(e.player == BLACK for e in a.recibidos)
    assert all(e.player == WHITE for e in b.recibidos)


def test_se_puede_empezar_desde_una_posicion_a_mitad_de_partida():
    a, b = Primero(), Primero()
    a_mitad = apply_move(initial_state(), (2, 3))  # ya les toca a las blancas
    resultado = play_game(a, b, a_mitad)
    assert b.recibidos[0] == a_mitad  # la primera jugada se le pide a player_b
    assert is_terminal(reproducir(resultado.moves, a_mitad))


def test_una_posicion_terminal_devuelve_el_resultado_sin_pedir_jugadas():
    final = reproducir(play_game(Primero(), Primero()).moves)
    a, b = Primero(), Primero()
    resultado = play_game(a, b, final)
    assert a.recibidos == [] and b.recibidos == []
    assert resultado.moves == ()
    assert resultado.winner == winner(final)


# -- Cada jugador recibe su propia copia del estado ------------------------ #


def test_cada_jugador_recibe_su_propio_objeto_de_estado():
    inicio = initial_state()
    a = Primero()
    play_game(a, Primero(), inicio)
    assert a.recibidos[0] == inicio
    assert a.recibidos[0] is not inicio


def test_un_bot_que_intenta_modificar_el_estado_solo_se_perjudica_a_si_mismo():
    class Tramposo:
        def choose_move(self, state: GameState) -> Move:
            state.player = WHITE  # type: ignore[misc]
            return legal_moves(state)[0]

    resultado = play_game(Tramposo(), Primero())
    assert resultado.winner == WHITE
    assert resultado.forfeit is not None
    assert resultado.moves == ()


# -- Bots rotos: fallan limpiamente ---------------------------------------- #


def test_un_bot_que_lanza_una_excepcion_pierde_la_partida():
    resultado = play_game(Falla(error=RuntimeError("boom")), Primero())
    assert resultado.winner == WHITE
    assert "RuntimeError" in (resultado.forfeit or "")
    assert "boom" in (resultado.forfeit or "")


def test_un_bot_que_devuelve_una_jugada_ilegal_pierde_la_partida():
    resultado = play_game(Primero(), Falla(jugada=(0, 0)))
    assert resultado.winner == BLACK
    assert "ilegal" in (resultado.forfeit or "")
    assert resultado.moves  # las jugadas anteriores quedan registradas


def test_un_bot_que_no_devuelve_nada_pierde_la_partida():
    resultado = play_game(Falla(jugada=None), Primero())
    assert resultado.winner == WHITE
    assert "None" in (resultado.forfeit or "")


def test_un_bot_que_devuelve_basura_pierde_la_partida():
    for basura in ["d3", 7, (1, 2, 3), (2.0, 3), [2, "x"], (True, 3)]:
        resultado = play_game(Falla(jugada=basura), Primero())
        assert resultado.winner == WHITE, basura
        assert resultado.forfeit is not None


def test_la_jugada_ilegal_no_entra_en_el_historial():
    resultado = play_game(Primero(), Falla(jugada=(0, 0)))
    assert (0, 0) not in resultado.moves


def test_una_jugada_en_forma_de_lista_se_acepta_y_se_guarda_como_tupla():
    class ConLista:
        def choose_move(self, state: GameState):
            return list(legal_moves(state)[0])

    resultado = play_game(ConLista(), ConLista())
    assert resultado.forfeit is None
    assert all(isinstance(m, tuple) for m in resultado.moves)


# -- El ejecutor es silencioso --------------------------------------------- #


def test_play_game_no_imprime_nada():
    salida = io.StringIO()
    with redirect_stdout(salida):
        play_game(RandomPlayer.create(1), RandomPlayer.create(2))
    assert salida.getvalue() == ""


def test_el_ejecutor_no_depende_de_la_clase_player():
    """Solo necesita un objeto con choose_move: ni herencia ni identidad."""
    rng = random.Random(0)

    class Suelto:
        def choose_move(self, state: GameState) -> Move:
            return rng.choice(legal_moves(state))

    assert play_game(Suelto(), Suelto()).forfeit is None
