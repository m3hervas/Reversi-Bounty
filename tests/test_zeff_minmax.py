"""Tests del jugador minimax Zeff: identidad, jugadas legales, tiempo, que gana a los bots simples
y cada una de sus piezas (tablero en bits, desempates, final exacto y libro de aperturas)."""

from __future__ import annotations

import math
import random
import time

import pytest

from reversibounty import (
    BLACK,
    WHITE,
    GameState,
    Player,
    apply_move,
    flips,
    initial_state,
    is_legal,
    is_terminal,
    legal_moves,
    play_game,
    score,
)
from reversibounty.bots import GreedyPlayer, RandomPlayer, ZeffMinmaxPlayer
from reversibounty.bots import zeff_minmax as zeff
from reversibounty.bots.zeff_libro import LIBRO


def _determinista(semilla: int) -> ZeffMinmaxPlayer:
    """Una versión que juega igual en cualquier ordenador.

    Con un límite de tiempo corto, el bot llega a mirar más o menos jugadas hacia delante según lo
    rápida que sea la máquina (en el CI, menos), y el resultado de la partida cambiaba de una
    ejecución a otra. Aquí la profundidad es fija y el tiempo sobra, así que el tiempo nunca
    decide nada; y la semilla es la de la partida, para que los desempates también se repitan.
    """
    return ZeffMinmaxPlayer(random.Random(semilla), time_limit=60.0, max_depth=2)


def _posiciones(cuantas: int, semilla: int = 0, minimo: int = 0, maximo: int = 60) -> list[GameState]:
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


# -- Identidad y contrato ------------------------------------------------------- #


def test_zeff_minmax_es_un_player_con_identidad_valida():
    assert issubclass(ZeffMinmaxPlayer, Player)
    assert ZeffMinmaxPlayer.get_name()
    assert ZeffMinmaxPlayer.get_authors()
    assert ZeffMinmaxPlayer.get_description()
    assert len(ZeffMinmaxPlayer.get_icon()) >= 1


def test_zeff_minmax_elige_una_jugada_legal():
    estado = initial_state()
    assert is_legal(estado, ZeffMinmaxPlayer.create(0).choose_move(estado))


def test_zeff_minmax_elige_jugadas_legales_en_posiciones_variadas():
    bot = ZeffMinmaxPlayer(random.Random(1), time_limit=0.05)
    for estado in _posiciones(15, semilla=7):
        assert is_legal(estado, bot.choose_move(estado))


# -- El tiempo --------------------------------------------------------------------- #


def test_zeff_minmax_respeta_el_limite_de_tiempo():
    inicio = time.monotonic()
    ZeffMinmaxPlayer.create(0).choose_move(initial_state())
    assert time.monotonic() - inicio < 1.0


def test_ninguna_jugada_pasa_de_su_presupuesto_de_tiempo():
    """El presupuesto es de 0,5 s; con margen para un CI lento, nunca debe acercarse a 1 s."""
    bot = ZeffMinmaxPlayer(random.Random(2), use_book=False)
    for estado in _posiciones(6, semilla=3, minimo=10, maximo=40):
        inicio = time.perf_counter()
        bot.choose_move(estado)
        assert time.perf_counter() - inicio < zeff.DEFAULT_TIME_LIMIT + 0.3


def test_informa_de_como_ha_decidido():
    bot = ZeffMinmaxPlayer(random.Random(0), time_limit=0.2, use_book=False)
    bot.choose_move(_posiciones(1, semilla=5, minimo=10, maximo=20)[0])
    info = bot.last_search
    assert info["motivo"] == "búsqueda"
    assert info["profundidad"] >= 1 and info["nodos"] > 0
    assert {"valor", "exacto", "segundos"} <= set(info)


# -- El tablero en bits: calcula exactamente lo mismo que el motor -------------- #


def test_el_tablero_en_bits_da_las_mismas_jugadas_y_volteos_que_el_motor():
    for estado in _posiciones(300, semilla=11):
        p, o = zeff._bits(estado)
        jugadas = sorted(divmod(i, 8) for i in zeff._indices(zeff._jugadas(p, o)))
        assert jugadas == sorted(legal_moves(estado))
        for jugada in jugadas:
            bit = 1 << (jugada[0] * 8 + jugada[1])
            volteadas = sorted(divmod(i, 8) for i in zeff._indices(zeff._volteos(p, o, bit)))
            assert volteadas == sorted(flips(estado.board, estado.player, jugada))


# -- Los desempates de la raíz son empates de verdad ----------------------------- #


def _valor_exacto(bot: ZeffMinmaxPlayer, p: int, o: int, casilla: int, prof: int) -> int:
    """Valor de una jugada de la raíz con la ventana completa (sin poda que lo deforme)."""
    m = 1 << casilla
    f = zeff._volteos(p, o, m)
    bot._tabla = {}
    return -bot._buscar(o & ~f, p | m | f, prof - 1, -zeff._INF, zeff._INF)


def test_los_empates_de_la_raiz_no_cuelan_jugadas_peores():
    bot = ZeffMinmaxPlayer(random.Random(0), use_book=False)
    bot._limite = math.inf
    for estado in _posiciones(25, semilla=21, minimo=4, maximo=40):
        p, o = zeff._bits(estado)
        orden = bot._ordenar(zeff._jugadas(p, o), -1)
        if len(orden) < 2:
            continue
        bot._tabla = {}
        mejor, empatadas = bot._raiz(p, o, 3, orden)
        exactos = {c: _valor_exacto(bot, p, o, c, 3) for c in orden}
        assert mejor == max(exactos.values())
        assert all(exactos[c] == mejor for c in empatadas)


# -- El final exacto ----------------------------------------------------------------- #


def _resultado_perfecto(estado: GameState, yo: int) -> int:
    """Diferencia de fichas final para ``yo`` si los dos juegan perfecto (con el motor)."""
    if is_terminal(estado):
        negras, blancas = score(estado)
        return (negras - blancas) * yo
    valores = [_resultado_perfecto(apply_move(estado, m), yo) for m in legal_moves(estado)]
    return max(valores) if estado.player == yo else min(valores)


@pytest.mark.parametrize("semilla", range(4))
def test_con_pocas_casillas_vacias_resuelve_el_final_y_juega_perfecto(semilla):
    estado = _posiciones(1, semilla=100 + semilla, minimo=53, maximo=53)[0]
    bot = ZeffMinmaxPlayer(random.Random(semilla), time_limit=30.0, use_book=False)
    jugada = bot.choose_move(estado)
    if len(legal_moves(estado)) == 1:
        return
    assert bot.last_search["exacto"]
    yo = estado.player
    mejor = max(_resultado_perfecto(apply_move(estado, m), yo) for m in legal_moves(estado))
    assert _resultado_perfecto(apply_move(estado, jugada), yo) == mejor


# -- El libro de aperturas ------------------------------------------------------------ #


def test_el_libro_tiene_entradas_y_todas_son_jugadas_legales():
    assert LIBRO, "el libro está vacío: ejecuta scripts/generar_libro_zeff.py"
    for (p, o), casilla in LIBRO.items():
        assert (zeff._jugadas(p, o) >> casilla) & 1, f"jugada ilegal en el libro: {casilla}"


def test_el_libro_se_usa_en_la_apertura_y_con_cualquier_simetria():
    bot = ZeffMinmaxPlayer(random.Random(0))
    for jugada in legal_moves(initial_state()):  # las 4 primeras jugadas son simétricas
        estado = apply_move(initial_state(), jugada)
        respuesta = bot.choose_move(estado)
        assert bot.last_search["motivo"] == "libro"
        assert is_legal(estado, respuesta)


def test_sin_libro_piensa_tambien_la_apertura():
    bot = ZeffMinmaxPlayer(random.Random(0), time_limit=0.1, use_book=False)
    bot.choose_move(initial_state())
    assert bot.last_search["motivo"] == "búsqueda"


# -- La evaluación ------------------------------------------------------------------- #


def test_la_evaluacion_es_simetrica_entre_los_dos_jugadores():
    for estado in _posiciones(30, semilla=31):
        assert zeff.evaluate(estado, BLACK) == -zeff.evaluate(estado, WHITE)


def test_una_casilla_x_solo_resta_mientras_su_esquina_esta_vacia():
    tablero = [[0] * 8 for _ in range(8)]
    tablero[3][3] = tablero[4][4] = WHITE
    tablero[3][4] = tablero[4][3] = BLACK
    tablero[1][1] = BLACK  # casilla X de la esquina a1
    con_esquina_vacia = zeff.evaluate(GameState(tuple(map(tuple, tablero)), WHITE), BLACK)
    tablero[0][0] = BLACK  # ahora la esquina es suya
    con_esquina_propia = zeff.evaluate(GameState(tuple(map(tuple, tablero)), WHITE), BLACK)
    assert con_esquina_propia > con_esquina_vacia + zeff.CASTIGO_X


# -- Fuerza ------------------------------------------------------------------------------- #


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
