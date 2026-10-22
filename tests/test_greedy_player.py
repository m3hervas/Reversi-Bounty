"""Tests del jugador avaricioso (tarea 3.1): gana con claridad al aleatorio."""

from __future__ import annotations

from reversibounty import BLACK, WHITE, GameState, Player, initial_state, is_legal, play_game
from reversibounty.bots import GreedyPlayer, RandomPlayer
from reversibounty.bots.greedy_player import evaluate_move


def test_greedy_player_es_un_player_con_identidad_valida():
    assert issubclass(GreedyPlayer, Player)
    assert GreedyPlayer.get_name() == "avaricioso"
    assert GreedyPlayer.get_authors()
    assert GreedyPlayer.get_description()
    assert GreedyPlayer.get_icon() == "💰"


def test_greedy_player_siempre_elige_una_jugada_legal():
    estado = initial_state()
    assert is_legal(estado, GreedyPlayer.create(0).choose_move(estado))


def test_greedy_player_con_la_misma_semilla_repite_la_partida():
    a = play_game(GreedyPlayer.create(7), RandomPlayer.create(8))
    b = play_game(GreedyPlayer.create(7), RandomPlayer.create(8))
    assert a.moves == b.moves


def test_una_esquina_puntua_mas_que_su_casilla_vecina():
    filas = [[0] * 8 for _ in range(8)]
    filas[0][1], filas[0][2] = WHITE, BLACK  # jugar en (0, 0) captura (0, 1)
    filas[2][2], filas[3][3] = WHITE, BLACK  # jugar en (1, 1) captura (2, 2)
    estado = GameState(board=tuple(tuple(f) for f in filas), player=BLACK)
    assert evaluate_move(estado, (0, 0)) > evaluate_move(estado, (1, 1))


def test_greedy_player_gana_mas_del_80_por_ciento_al_aleatorio():
    victorias = 0
    for semilla in range(100):
        avaricioso = GreedyPlayer.create(semilla)
        aleatorio = RandomPlayer.create(semilla + 1000)
        if semilla % 2 == 0:  # la mitad de las partidas con cada color
            victorias += play_game(avaricioso, aleatorio).winner == BLACK
        else:
            victorias += play_game(aleatorio, avaricioso).winner == WHITE
    assert victorias > 80
