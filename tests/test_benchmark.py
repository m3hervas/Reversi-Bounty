"""Tests de la medición de bots: cuentas correctas, repetible y en los dos sentidos."""

from __future__ import annotations

import pytest

from reversibounty.benchmark import format_table, main, measure_all, measure_pair
from reversibounty.bots import GreedyPlayer, RandomPlayer


def test_las_cuentas_cuadran_y_se_juegan_los_dos_sentidos():
    r = measure_pair(GreedyPlayer, RandomPlayer, games=6, seed=1)
    assert r.games == 6
    assert r.a_wins + r.b_wins + r.draws == 6
    assert r.a_wins == r.a_wins_first + r.a_wins_second
    assert r.a_wins_first <= 3 and r.a_wins_second <= 3


def test_la_misma_semilla_da_el_mismo_resultado():
    a = measure_pair(GreedyPlayer, RandomPlayer, games=4, seed=5)
    b = measure_pair(GreedyPlayer, RandomPlayer, games=4, seed=5)
    assert a == b


def test_el_avaricioso_gana_al_aleatorio_con_los_dos_colores():
    r = measure_pair(GreedyPlayer, RandomPlayer, games=10, seed=0)
    assert r.a_rate_first >= 60 and r.a_rate_second >= 60


@pytest.mark.parametrize("partidas", [0, 1, 3])
def test_un_numero_de_partidas_invalido_da_error(partidas):
    with pytest.raises(ValueError):
        measure_pair(GreedyPlayer, RandomPlayer, games=partidas)


def test_la_tabla_dice_cuantas_partidas_se_jugaron():
    texto = format_table(
        measure_all({"aleatorio": RandomPlayer, "avaricioso": GreedyPlayer}, games=4, seed=2),
        seed=2,
    )
    assert "aleatorio" in texto and "avaricioso" in texto
    assert "de 4 partidas" in texto and "semilla 2" in texto


def test_el_comando_imprime_la_tabla(capsys):
    codigo = main(["--partidas", "2", "--jugadores", "aleatorio", "avaricioso"])
    assert codigo == 0
    assert "Tasas de victoria" in capsys.readouterr().out
