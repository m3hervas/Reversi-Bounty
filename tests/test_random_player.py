"""Tests del jugador de referencia (paso 2.2): dos jugadores aleatorios juegan sin trampas."""

from __future__ import annotations

import pytest

from reversibounty import Player, initial_state, is_legal, play_game
from reversibounty.bots import RandomPlayer


def test_random_player_es_un_player_con_identidad_valida():
    assert issubclass(RandomPlayer, Player)
    assert RandomPlayer.get_name() == "Aleatorio"
    assert RandomPlayer.get_authors()
    assert RandomPlayer.get_description()
    assert RandomPlayer.get_icon() == "🃏"


@pytest.mark.parametrize("semilla", [0, 1, 2, 3, 4])
def test_dos_random_player_juegan_una_partida_completa_sin_jugadas_ilegales(semilla):
    resultado = play_game(RandomPlayer.create(semilla), RandomPlayer.create(semilla + 100))
    assert resultado.forfeit is None  # nadie perdió por una jugada ilegal
    assert resultado.moves


def test_random_player_con_la_misma_semilla_repite_la_partida():
    a = play_game(RandomPlayer.create(42), RandomPlayer.create(43))
    b = play_game(RandomPlayer.create(42), RandomPlayer.create(43))
    assert a.moves == b.moves


def test_random_player_con_otra_semilla_cambia_la_partida():
    a = play_game(RandomPlayer.create(1), RandomPlayer.create(2))
    b = play_game(RandomPlayer.create(3), RandomPlayer.create(4))
    assert a.moves != b.moves


def test_random_player_siempre_elige_una_jugada_legal():
    jugador = RandomPlayer.create(0)
    estado = initial_state()
    for _ in range(20):
        assert is_legal(estado, jugador.choose_move(estado))
