"""El jugador minimax: mira varias jugadas hacia delante antes de elegir.

Usa **minimax con poda alfa-beta** y **profundización iterativa**: busca primero a
profundidad 1, luego 2, 3... y se queda con la mejor jugada de la última profundidad que
llegó a terminar antes de agotar su presupuesto de tiempo. Así nunca se pasa del límite del
torneo (1 s por jugada) y, si le sobra tiempo, mira más lejos.

La evaluación de una posición, desde el punto de vista del bot, suma:

* **Valor de las casillas** (esquinas muy buenas, casillas pegadas a la esquina malas),
  reutilizando la tabla ``SQUARE_WEIGHTS`` del jugador Wapol voraz.
* **Movilidad**: tener más jugadas legales que el rival es una ventaja.
* **Final de partida**: si la posición es terminal, solo cuenta la diferencia de fichas,
  con un peso enorme para que ganar siempre pese más que cualquier otra cosa.
"""

from __future__ import annotations

import random
import time

from ..game import (
    GameState,
    Move,
    apply_move,
    is_terminal,
    legal_moves,
    opponent,
    score,
)
from ..player import Player
from .greedy_player import CORNERS, SQUARE_WEIGHTS

#: Segundos que el bot se da a sí mismo por jugada (el torneo permite 1 s por defecto).
DEFAULT_TIME_LIMIT = 0.5

#: Profundidad máxima de la búsqueda, aunque sobre tiempo.
MAX_DEPTH = 8

#: Peso de la movilidad en la evaluación.
MOBILITY_WEIGHT = 5

#: Valor de una partida ganada o perdida: mayor que cualquier evaluación intermedia.
WIN_VALUE = 100_000


class _OutOfTime(Exception):
    """Se agotó el tiempo a mitad de una búsqueda: se descarta esa profundidad."""


def evaluate(state: GameState, me: int) -> int:
    """Valora una posición para el jugador ``me``: cuanto más alta, mejor para él."""
    if is_terminal(state):
        negras, blancas = score(state)
        diferencia = (negras - blancas) * me
        if diferencia > 0:
            return WIN_VALUE + diferencia
        if diferencia < 0:
            return -WIN_VALUE + diferencia
        return 0

    posicional = 0
    for fila, pesos in enumerate(SQUARE_WEIGHTS):
        for columna, peso in enumerate(pesos):
            posicional += state.board[fila][columna] * me * peso

    mis_jugadas = len(legal_moves(state if state.player == me else _con_turno(state, me)))
    sus_jugadas = len(
        legal_moves(state if state.player != me else _con_turno(state, opponent(me)))
    )
    return posicional + MOBILITY_WEIGHT * (mis_jugadas - sus_jugadas)


def _con_turno(state: GameState, player: int) -> GameState:
    """La misma posición pero con el turno de ``player`` (solo para contar jugadas)."""
    return GameState(board=state.board, player=player)


class ZeffMinmaxPlayer(Player):
    """Minimax con poda alfa-beta y límite de tiempo."""

    def __init__(
        self,
        rng: random.Random | None = None,
        time_limit: float = DEFAULT_TIME_LIMIT,
        max_depth: int = MAX_DEPTH,
    ) -> None:
        self._rng = rng if rng is not None else random.Random()
        self._time_limit = time_limit
        self._max_depth = max_depth
        self._deadline = 0.0

    @classmethod
    def get_name(cls) -> str:
        return "Zeff minimax"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Marcos Felgueroso"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Minimax con poda alfa-beta y profundidad adaptada al tiempo: mira varias "
            "jugadas hacia delante valorando esquinas y movilidad."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "👨‍🍳"

    @classmethod
    def create(cls, seed: int) -> ZeffMinmaxPlayer:
        """Con la misma semilla desempata igual, para repetir partidas."""
        return cls(random.Random(seed))

    def choose_move(self, state: GameState) -> Move:
        jugadas = legal_moves(state)
        if len(jugadas) == 1:
            return jugadas[0]

        self._deadline = time.monotonic() + self._time_limit
        # Respuesta de seguridad por si ni la profundidad 1 llega a acabar.
        mejor = self._rng.choice(jugadas)
        for profundidad in range(1, self._max_depth + 1):
            try:
                mejor = self._buscar_raiz(state, jugadas, profundidad)
            except _OutOfTime:
                break
        return mejor

    # -- Búsqueda ------------------------------------------------------------ #

    def _buscar_raiz(self, state: GameState, jugadas: list[Move], profundidad: int) -> Move:
        me = state.player
        # Las esquinas se miran primero: mejora mucho la poda.
        jugadas = sorted(jugadas, key=lambda m: m not in CORNERS)
        mejor_valor = -float("inf")
        mejores: list[Move] = []
        for jugada in jugadas:
            valor = self._minimax(
                apply_move(state, jugada), profundidad - 1, mejor_valor, float("inf"), me
            )
            if valor > mejor_valor:
                mejor_valor, mejores = valor, [jugada]
            elif valor == mejor_valor:
                mejores.append(jugada)
        return self._rng.choice(mejores)

    def _minimax(
        self, state: GameState, profundidad: int, alfa: float, beta: float, me: int
    ) -> float:
        if time.monotonic() > self._deadline:
            raise _OutOfTime
        if profundidad == 0 or is_terminal(state):
            return evaluate(state, me)

        jugadas = legal_moves(state)
        # El motor gestiona los pases solo, así que quien mueve se mira en el estado.
        if state.player == me:
            valor = -float("inf")
            for jugada in jugadas:
                valor = max(
                    valor, self._minimax(apply_move(state, jugada), profundidad - 1, alfa, beta, me)
                )
                alfa = max(alfa, valor)
                if alfa >= beta:
                    break
            return valor
        valor = float("inf")
        for jugada in jugadas:
            valor = min(
                valor, self._minimax(apply_move(state, jugada), profundidad - 1, alfa, beta, me)
            )
            beta = min(beta, valor)
            if alfa >= beta:
                break
        return valor
