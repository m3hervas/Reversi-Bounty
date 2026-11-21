"""Las figuras de «Leyes del mar» dicen lo mismo que el motor.

Cada tablero de ejemplo de la web (atributo data-mini) se reconstruye y se comprueba con
reversibounty: si alguien cambia un dibujo y deja de ser una posición correcta, falla aquí.
"""

from __future__ import annotations

import re
from pathlib import Path

from reversibounty.game import (
    GameState,
    apply_move,
    initial_state,
    is_terminal,
    legal_moves,
    score,
    str_to_move,
)

HTML = (Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(encoding="utf-8")
REGLAS = HTML[HTML.index('data-view="reglas"'):HTML.index('data-view="bots"')]
MINIS = re.findall(r'data-mini="([^"]+)"', REGLAS)
VALOR = {"s": 1, "S": 1, "h": -1, "H": -1}


def tablero(mini: str) -> list[list[int]]:
    return [[VALOR.get(ch, 0) for ch in fila] for fila in mini.split("|")]


def estado(mini: str, jugador: int) -> GameState:
    return GameState.from_dict({"board": tablero(mini), "player": jugador})


def jugadas(mini: str) -> set[tuple[int, int]]:
    """Las casillas marcadas con la brújula (t) en una figura."""
    return {(r, c) for r, fila in enumerate(mini.split("|")) for c, ch in enumerate(fila) if ch == "t"}


def test_hay_siete_figuras_de_tablero():
    assert len(MINIS) == 7  # salida, antes/después, paso, dos finales y el mapa


def test_la_salida_y_sus_cuatro_jugadas():
    salida = MINIS[0]
    assert [list(f) for f in initial_state().board] == tablero(salida)
    assert set(legal_moves(initial_state())) == jugadas(salida)


def test_capturar_en_dos_direcciones():
    antes, despues = MINIS[1], MINIS[2]
    resultado = apply_move(estado(antes, 1), str_to_move("f3"))
    assert [list(f) for f in resultado.board] == tablero(despues)


def test_el_ejemplo_de_paso():
    figura = MINIS[3]
    calaveras = estado(figura, 1)
    assert legal_moves(calaveras) == [] and not is_terminal(calaveras)
    assert jugadas(figura) == {str_to_move("f5")}
    assert str_to_move("f5") in legal_moves(estado(figura, -1))


def test_los_dos_finales():
    lleno, anticipado = estado(MINIS[4], 1), estado(MINIS[5], 1)
    assert is_terminal(lleno) and score(lleno) == (26, 38)  # «38 a 26 para los sombreros»
    assert is_terminal(anticipado) and score(anticipado) == (13, 0)


def test_el_final_anticipado_se_puede_alcanzar_de_verdad():
    # La misma partida que cuenta docs/reglas.md.
    s = initial_state()
    for jugada in "e6 f4 e3 f6 g5 d6 e7 f5 c5".split():
        s = apply_move(s, str_to_move(jugada))
    assert [list(f) for f in s.board] == tablero(MINIS[5])
