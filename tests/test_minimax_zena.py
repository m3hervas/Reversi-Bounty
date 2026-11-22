"""Tests del bot Minimax de Zena: el tablero en bits calcula lo mismo que el motor, la
evaluación es simétrica, los empates de la raíz son de verdad y el final se juega perfecto."""

from __future__ import annotations

import math
import random
import sys

import pytest

from reversibounty import (
    GameState,
    apply_move,
    flips,
    initial_state,
    is_legal,
    is_terminal,
    legal_moves,
    score,
)
from reversibounty.manifest import load_players

MinimaxZena = load_players()["Minimax de Zena"]
mz = sys.modules[MinimaxZena.__module__]


def _posiciones(
    cuantas: int, semilla: int = 0, minimo: int = 0, maximo: int = 60
) -> list[GameState]:
    """Posiciones de partidas aleatorias, tras entre ``minimo`` y ``maximo`` jugadas."""
    rng = random.Random(semilla)
    resultado = []
    while len(resultado) < cuantas:
        estado = initial_state()
        for _ in range(rng.randrange(minimo, maximo + 1)):
            if is_terminal(estado):
                break
            estado = apply_move(estado, rng.choice(legal_moves(estado)))
        if not is_terminal(estado):
            resultado.append(estado)
    return resultado


def _casillas(b: int) -> list[tuple[int, int]]:
    return sorted(mz.casilla(x) for x in mz.separar(b))


def test_el_tablero_en_bits_da_las_mismas_jugadas_y_volteos_que_el_motor():
    for estado in _posiciones(2000, semilla=11):
        yo, el = mz.a_bits(estado)
        jugadas = _casillas(mz.jugadas(yo, el))
        assert jugadas == sorted(legal_moves(estado))
        for jugada in jugadas:
            volteadas = _casillas(mz.volteos(yo, el, mz.bit(*jugada)))
            assert volteadas == sorted(flips(estado.board, estado.player, jugada))


def test_la_evaluacion_es_simetrica_entre_los_dos_jugadores():
    for estado in _posiciones(300, semilla=12):
        yo, el = mz.a_bits(estado)
        a = mz.evaluar(yo, el, mz.jugadas(yo, el).bit_count())
        b = mz.evaluar(el, yo, mz.jugadas(el, yo).bit_count())
        # Lo que es bueno para uno es igual de malo para el otro.
        assert a == -b


def test_elige_jugadas_legales_en_posiciones_variadas():
    bot = MinimaxZena.create(seed=0)
    for estado in _posiciones(30, semilla=13):
        assert is_legal(estado, bot.choose_move(estado))


def _valor_exacto(bot, yo: int, el: int, jugada: int, prof: int) -> int:
    """Valor de una jugada de la raíz con la ventana completa (sin poda que lo deforme)."""
    v = mz.volteos(yo, el, jugada)
    return -bot._negamax(el & ~v, yo | jugada | v, prof - 1, -mz.INFINITO, mz.INFINITO)


def test_los_empates_de_la_raiz_no_cuelan_jugadas_peores():
    bot = MinimaxZena.create(seed=0)
    bot._limite = math.inf
    for estado in _posiciones(25, semilla=21, minimo=4, maximo=40):
        yo, el = mz.a_bits(estado)
        candidatas = mz.separar(mz.jugadas(yo, el))
        if len(candidatas) < 2:
            continue
        mejor, empatadas = bot._raiz(yo, el, candidatas, 3)
        exactos = {j: _valor_exacto(bot, yo, el, j, 3) for j in candidatas}
        assert mejor == max(exactos.values())
        assert sorted(empatadas) == sorted(j for j in candidatas if exactos[j] == mejor)


def _resultado_perfecto(estado: GameState, yo: int) -> int:
    """Diferencia de fichas final para ``yo`` si los dos juegan perfecto (con el motor)."""
    if is_terminal(estado):
        negras, blancas = score(estado)
        return (negras - blancas) * yo
    valores = [_resultado_perfecto(apply_move(estado, m), yo) for m in legal_moves(estado)]
    return max(valores) if estado.player == yo else min(valores)


@pytest.mark.parametrize("semilla", range(4))
def test_con_pocas_casillas_vacias_no_desperdicia_una_victoria(semilla, monkeypatch):
    monkeypatch.setattr(mz, "TIEMPO_POR_JUGADA", 30.0)
    estado = _posiciones(1, semilla=100 + semilla, minimo=53, maximo=53)[0]
    bot = MinimaxZena.create(seed=semilla)
    jugada = bot.choose_move(estado)
    yo = estado.player
    mejor = max(_resultado_perfecto(apply_move(estado, m), yo) for m in legal_moves(estado))
    obtenido = _resultado_perfecto(apply_move(estado, jugada), yo)
    # Si había una jugada ganadora, la que elige también gana (o empata si lo mejor era empatar).
    if mejor > 0:
        assert obtenido > 0
    elif mejor == 0:
        assert obtenido == 0
