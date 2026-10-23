"""El jugador avaricioso: aplica una regla práctica sin mirar hacia delante.

Puntúa cada jugada legal con una regla sencilla sobre el Reversi y juega la que más puntúa;
los empates se deshacen al azar. La regla combina cuatro cosas:

* **Capturar mucho**: un punto por cada ficha que se da la vuelta.
* **Buenas casillas**: las esquinas valen mucho (nunca se pueden voltear), los bordes algo, y
  las casillas pegadas a una esquina vacía restan, porque se la regalan al rival.
* **No regalar esquinas**: si después de la jugada el rival puede ocupar una esquina, se
  penaliza.
* **Ahogar al rival**: resta por cada jugada que le quede al rival, para dejarle sin opciones
  buenas (controlar el tablero).

No hay búsqueda ni inteligencia real, pero basta para ganar con claridad al aleatorio. Sirve
de segunda vara de medir, y :func:`evaluate_move` puede reutilizarse como función de
evaluación en un bot con búsqueda.
"""

from __future__ import annotations

import random

from ..game import EMPTY, GameState, Move, apply_move, flips, legal_moves, opponent
from ..player import Player

#: Valor de cada casilla: esquinas muy buenas, sus vecinas malas, bordes buenos.
SQUARE_WEIGHTS: tuple[tuple[int, ...], ...] = (
    (100, -20, 10, 5, 5, 10, -20, 100),
    (-20, -50, -2, -2, -2, -2, -50, -20),
    (10, -2, 1, 1, 1, 1, -2, 10),
    (5, -2, 1, 0, 0, 1, -2, 5),
    (5, -2, 1, 0, 0, 1, -2, 5),
    (10, -2, 1, 1, 1, 1, -2, 10),
    (-20, -50, -2, -2, -2, -2, -50, -20),
    (100, -20, 10, 5, 5, 10, -20, 100),
)

CORNERS: tuple[Move, ...] = ((0, 0), (0, 7), (7, 0), (7, 7))

#: Penalización por cada esquina que el rival podría ocupar tras la jugada.
CORNER_GIFT_PENALTY = 100

#: Penalización por cada jugada legal que le quede al rival tras la jugada.
RIVAL_MOBILITY_PENALTY = 5


def evaluate_move(state: GameState, move: Move) -> int:
    """Puntúa una jugada legal de ``state.player``: cuanto más alta, mejor.

    Args:
        state: la posición actual, sin modificar.
        move: una jugada legal ``(fila, columna)``.

    Returns:
        Fichas capturadas, más el valor de la casilla, menos una penalización por cada
        esquina que la jugada deje al alcance del rival y por cada jugada que le deje.
    """
    me = state.player
    row, col = move
    captured = len(flips(state.board, me, move))
    after = apply_move(state, move)
    board = after.board
    rival = opponent(me)
    gifted = sum(
        1 for corner in CORNERS
        if board[corner[0]][corner[1]] == EMPTY and flips(board, rival, corner)
    )
    rival_moves = len(legal_moves(after)) if after.player == rival else 0  # 0 si pasa
    return (
        captured
        + SQUARE_WEIGHTS[row][col]
        - CORNER_GIFT_PENALTY * gifted
        - RIVAL_MOBILITY_PENALTY * rival_moves
    )


class GreedyPlayer(Player):
    """Juega la jugada legal mejor puntuada por :func:`evaluate_move`."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    @classmethod
    def get_name(cls) -> str:
        return "Avaricioso"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Reversi Bounty"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Captura lo máximo posible, busca esquinas y bordes, no regala esquinas y deja "
            "al rival sin jugadas, sin mirar hacia delante."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "💰"

    @classmethod
    def create(cls, seed: int) -> GreedyPlayer:
        """Con la misma semilla deshace los empates igual, para repetir partidas."""
        return cls(random.Random(seed))

    def choose_move(self, state: GameState) -> Move:
        scored = [(evaluate_move(state, move), move) for move in legal_moves(state)]
        best = max(score for score, _ in scored)
        return self._rng.choice([move for score, move in scored if score == best])
