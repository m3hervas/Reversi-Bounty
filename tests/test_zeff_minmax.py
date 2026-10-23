"""Tests del jugador minimax: identidad, jugadas legales y que gana a los bots simples."""

from __future__ import annotations

import random
import time

from reversibounty import BLACK, Player, initial_state, is_legal, play_game
from reversibounty.bots import GreedyPlayer, RandomPlayer, ZeffMinmaxPlayer


def _determinista(semilla: int) -> ZeffMinmaxPlayer:
    """Una versión que juega igual en cualquier ordenador.

    Con un límite de tiempo corto, el bot llega a mirar más o menos jugadas hacia delante según lo
    rápida que sea la máquina (en el CI, menos), y el resultado de la partida cambiaba de una
    ejecución a otra. Aquí la profundidad es fija y el tiempo sobra, así que el tiempo nunca
    decide nada; y la semilla es la de la partida, para que los desempates también se repitan.
    """
    return ZeffMinmaxPlayer(random.Random(semilla), time_limit=60.0, max_depth=2)


def test_zeff_minmax_es_un_player_con_identidad_valida():
    assert issubclass(ZeffMinmaxPlayer, Player)
    assert ZeffMinmaxPlayer.get_name()
    assert ZeffMinmaxPlayer.get_authors()
    assert ZeffMinmaxPlayer.get_description()
    assert len(ZeffMinmaxPlayer.get_icon()) >= 1


def test_zeff_minmax_elige_una_jugada_legal():
    estado = initial_state()
    assert is_legal(estado, ZeffMinmaxPlayer.create(0).choose_move(estado))


def test_zeff_minmax_respeta_el_limite_de_tiempo():
    inicio = time.monotonic()
    ZeffMinmaxPlayer.create(0).choose_move(initial_state())
    assert time.monotonic() - inicio < 1.0


def _victorias(rival_cls, partidas: int) -> int:
    victorias = 0
    for semilla in range(partidas):
        minimax = _determinista(semilla)
        rival = rival_cls.create(semilla + 1000)
        if semilla % 2 == 0:  # la mitad de las partidas con cada color
            victorias += play_game(minimax, rival).winner == BLACK
        else:
            victorias += play_game(rival, minimax).winner == -BLACK
    return victorias


def test_zeff_minmax_gana_al_menos_el_80_por_ciento_al_aleatorio():
    assert _victorias(RandomPlayer, 10) >= 8  # el 80 % de las partidas


def test_zeff_minmax_gana_mas_de_la_mitad_al_avaricioso():
    assert _victorias(GreedyPlayer, 10) >= 6
