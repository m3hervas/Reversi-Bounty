"""Los diagramas de la página de Reglas: cada afirmación del texto es verdad para el motor.

``web/data/reglas.json`` guarda, para cada diagrama, las jugadas que lo producen, las casillas que
se señalan ('marcas') y lo que la página dice de él ('esperado'). Aquí se reproduce cada diagrama con
el motor de Python y se comprueba cada afirmación, así que un pie de figura no puede decir algo que
el juego no haga: las jugadas posibles, las fichas que se voltean, las que cierran la línea, la
casilla donde no se puede jugar, el paso de turno, los finales y el mapa de esquinas.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from reversibounty import (
    BLACK,
    WHITE,
    GameState,
    apply_move,
    flips,
    initial_state,
    is_terminal,
    legal_moves,
    move_to_str,
    score,
    str_to_move,
    winner,
)
from reversibounty.game import DIRECTIONS, SIZE

RAIZ = Path(__file__).resolve().parent.parent
DATOS = json.loads((RAIZ / "web" / "data" / "reglas.json").read_text(encoding="utf-8"))["diagramas"]
HTML = (RAIZ / "web" / "index.html").read_text(encoding="utf-8")
JS = (RAIZ / "web" / "js" / "reglas.js").read_text(encoding="utf-8")


def reproducir(jugadas: list[str]) -> tuple[GameState, GameState]:
    """Devuelve (posición anterior a la última jugada, posición final)."""
    antes = estado = initial_state()
    for texto in jugadas:
        antes, estado = estado, apply_move(estado, str_to_move(texto))
    return antes, estado


def casillas(estado: GameState, color: int) -> set[str]:
    return {
        move_to_str((fila, columna))
        for fila in range(SIZE)
        for columna in range(SIZE)
        if estado.board[fila][columna] == color
    }


def volteadas(antes: GameState, despues: GameState) -> set[str]:
    return {
        move_to_str((fila, columna))
        for fila in range(SIZE)
        for columna in range(SIZE)
        if antes.board[fila][columna] not in (0, despues.board[fila][columna])
    }


def anclas(estado: GameState, destino: str) -> set[str]:
    """Las fichas del jugador que mueve que cierran cada línea de fichas rivales encerradas."""
    fila, columna = str_to_move(destino)
    propio, rival = estado.player, -estado.player
    cierran: set[str] = set()
    for dfila, dcolumna in DIRECTIONS:
        f, c, vistas = fila + dfila, columna + dcolumna, 0
        while 0 <= f < SIZE and 0 <= c < SIZE and estado.board[f][c] == rival:
            f, c, vistas = f + dfila, c + dcolumna, vistas + 1
        if vistas and 0 <= f < SIZE and 0 <= c < SIZE and estado.board[f][c] == propio:
            cierran.add(move_to_str((f, c)))
    return cierran


def esquinas_x_c() -> tuple[set[str], set[str], set[str]]:
    """Las casillas especiales, calculadas a partir de la geometría del tablero."""
    ultimo = SIZE - 1
    esquinas = {(0, 0), (0, ultimo), (ultimo, 0), (ultimo, ultimo)}
    x: set[tuple[int, int]] = set()
    c: set[tuple[int, int]] = set()
    for fila, columna in esquinas:
        paso_f = 1 if fila == 0 else -1
        paso_c = 1 if columna == 0 else -1
        x.add((fila + paso_f, columna + paso_c))
        c.add((fila + paso_f, columna))
        c.add((fila, columna + paso_c))
    nombrar = lambda conjunto: {move_to_str(m) for m in conjunto}  # noqa: E731
    return nombrar(esquinas), nombrar(x), nombrar(c)


@pytest.mark.parametrize("nombre", sorted(DATOS))
def test_las_jugadas_de_cada_diagrama_son_legales(nombre):
    estado = initial_state()
    for texto in DATOS[nombre]["jugadas"]:
        assert str_to_move(texto) in legal_moves(estado), f"{texto} no es legal en {nombre}"
        estado = apply_move(estado, str_to_move(texto))


@pytest.mark.parametrize("nombre", sorted(DATOS))
def test_lo_que_dice_cada_diagrama_lo_confirma_el_motor(nombre):
    esperado = DATOS[nombre]["esperado"]
    antes, estado = reproducir(DATOS[nombre]["jugadas"])

    if "turno" in esperado:
        assert estado.player == esperado["turno"]
    if "legales" in esperado:
        assert sorted(move_to_str(m) for m in legal_moves(estado)) == sorted(esperado["legales"])
    if "no_legales" in esperado:
        legales = {move_to_str(m) for m in legal_moves(estado)}
        assert not legales & set(esperado["no_legales"])
    if "puntos" in esperado:
        assert list(score(estado)) == esperado["puntos"]
    if "blancas" in esperado:
        assert set(esperado["blancas"]) <= casillas(estado, WHITE)
    if "negras" in esperado:
        assert set(esperado["negras"]) <= casillas(estado, BLACK)
    if "volteadas" in esperado:
        assert volteadas(antes, estado) == set(esperado["volteadas"])
    if "terminal" in esperado:
        assert is_terminal(estado) is esperado["terminal"]
    if "ganador" in esperado:
        assert winner(estado) == esperado["ganador"]
    if "vacias" in esperado:
        assert SIZE * SIZE - sum(score(estado)) == esperado["vacias"]
    if "pasa" in esperado:
        # Pasa quien no puede mover: el turno vuelve a quien acaba de jugar.
        assert (estado.player == antes.player and not is_terminal(estado)) is esperado["pasa"]


def test_el_destino_de_la_captura_es_legal_y_voltea_justo_lo_que_se_senala():
    diagrama = DATOS["antes-f3"]
    _, estado = reproducir(diagrama["jugadas"])
    destino = diagrama["esperado"]["destino"]
    assert str_to_move(destino) in legal_moves(estado), "el destino señalado no es una jugada legal"
    voltea = {move_to_str(m) for m in flips(estado.board, estado.player, str_to_move(destino))}
    assert voltea == set(diagrama["esperado"]["volteables"])


def test_las_fichas_que_cierran_la_linea_son_las_que_dice_el_diagrama():
    diagrama = DATOS["antes-f3"]
    _, estado = reproducir(diagrama["jugadas"])
    assert anclas(estado, diagrama["esperado"]["destino"]) == set(diagrama["esperado"]["anclas"])


def test_lo_que_se_voltea_antes_es_lo_que_aparece_volteado_despues():
    antes_f3 = DATOS["antes-f3"]["esperado"]["volteables"]
    despues_f3 = DATOS["despues-f3"]["esperado"]["volteadas"]
    assert sorted(antes_f3) == sorted(despues_f3)
    assert DATOS["antes-f3"]["jugadas"] + [DATOS["antes-f3"]["esperado"]["destino"]] == DATOS["despues-f3"]["jugadas"]


def test_c3_no_encierra_ninguna_ficha_como_dice_el_texto():
    estado = initial_state()
    c3 = str_to_move("c3")
    assert c3 not in legal_moves(estado)
    assert flips(estado.board, estado.player, c3) == []
    assert DATOS["c3-prohibida"]["marcas"]["prohibidas"] == ["c3"]


def test_las_esquinas_las_casillas_x_y_las_c_del_mapa_son_las_correctas():
    esquinas, x, c = esquinas_x_c()
    esperado = DATOS["mapa"]["esperado"]
    assert set(esperado["esquinas"]) == esquinas
    assert set(esperado["x"]) == x
    assert set(esperado["c"]) == c
    assert len(c) == 8  # el texto dice que hay ocho casillas C


@pytest.mark.parametrize("nombre", sorted(DATOS))
def test_las_marcas_del_diagrama_coinciden_con_lo_verificado(nombre):
    """Lo que se señala sobre el tablero es exactamente lo que el test ha comprobado."""
    marcas, esperado = DATOS[nombre]["marcas"], DATOS[nombre]["esperado"]
    for grupo in ("volteables", "anclas", "esquinas", "x", "c"):
        if grupo in marcas:
            assert sorted(marcas[grupo]) == sorted(esperado[grupo]), f"{nombre}: «{grupo}» no coincide"
    if "destino" in marcas:
        assert marcas["destino"] == [esperado["destino"]]
    if "prohibidas" in marcas:
        assert set(marcas["prohibidas"]) <= set(esperado["no_legales"])


def test_el_final_lleno_es_un_final_habitual_y_el_anticipado_no():
    _, lleno = reproducir(DATOS["final-lleno"]["jugadas"])
    _, temprano = reproducir(DATOS["final-temprano"]["jugadas"])
    assert sum(score(lleno)) == 64 and is_terminal(lleno)
    assert sum(score(temprano)) < 64 and is_terminal(temprano)


def test_el_paso_de_turno_pasa_de_verdad():
    antes, estado = reproducir(DATOS["paso"]["jugadas"])
    quien_paso = -antes.player  # el rival de quien acaba de jugar
    assert estado.player == antes.player and not is_terminal(estado)
    assert not legal_moves(GameState(estado.board, quien_paso))  # el que pasa no tiene jugadas


def test_los_diagramas_de_la_pagina_y_los_del_json_son_los_mismos():
    en_html = set(re.findall(r'data-diagram="([^"]+)"', HTML))
    assert en_html == set(DATOS), "hay diagramas en el HTML sin datos, o datos sin usar"


def test_cada_diagrama_tiene_las_opciones_que_usa_la_pagina():
    for nombre, diagrama in DATOS.items():
        for clave in ("etiqueta", "jugadas", "pistas", "ultima", "volteadas", "marcas", "esperado"):
            assert clave in diagrama, f"{nombre} no tiene «{clave}»"
        assert diagrama["etiqueta"].strip(), f"{nombre} no tiene etiqueta accesible"


def test_todos_los_tipos_de_marca_del_json_los_conoce_el_javascript():
    usados = {grupo for diagrama in DATOS.values() for grupo in diagrama["marcas"]}
    conocidos = set(re.findall(r"(\w+):\s*\"(?:flip|anchor|target|deny|corner|x|c)\"", JS))
    assert usados <= conocidos, f"reglas.js no conoce estas marcas: {usados - conocidos}"
