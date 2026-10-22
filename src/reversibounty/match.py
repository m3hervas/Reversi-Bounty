"""El ejecutor de partidas: juega una partida completa entre dos jugadores.

``play_game`` no sabe nada de personas, bots ni torneos: solo necesita dos objetos con un
método ``choose_move``, que es lo que ofrece :class:`~reversibounty.player.Player`. Así el
mismo ejecutor sirve para el torneo, la web y los tests.

Un bot no es de fiar: puede devolver una casilla ocupada, ``None`` o un texto, o lanzar una
excepción. Por eso cada jugada se valida antes de aplicarla, y quien incumple pierde esa
partida con el motivo anotado, en lugar de romper el programa. Esa regla vive en un solo sitio,
:func:`request_move`, y la usan tanto ``play_game`` como la web.

Cada jugador recibe su propio objeto de estado. Como :class:`~reversibounty.game.GameState` es
inmutable, un bot que intente modificarlo no puede: falla y solo se perjudica a sí mismo.

El ejecutor no pone límites de tiempo; eso corresponde a quien organice un torneo.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from .game import (
    BLACK,
    GameState,
    Move,
    apply_move,
    color_name,
    initial_state,
    is_legal,
    is_terminal,
    opponent,
    score,
    winner,
)


class Mover(Protocol):
    """Cualquier objeto que sepa elegir una jugada; un ``Player`` lo cumple."""

    def choose_move(self, state: GameState) -> Move: ...


class Forfeit(Exception):
    """Un jugador pierde la partida por incumplir las reglas.

    Attributes:
        reason: lo que hizo mal, por ejemplo ``"devolvió una jugada ilegal: (3, 3)"``.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class GameResult:
    """El resultado de una partida.

    Attributes:
        winner: :data:`~reversibounty.game.BLACK`, :data:`~reversibounty.game.WHITE` o ``0``
            si hubo empate.
        moves: las jugadas, en orden, que llevan de la posición inicial hasta el final.
            No incluye la jugada ilegal que haya hecho perder, si la hubo.
        score: ``(fichas_negras, fichas_blancas)`` al terminar la partida.
        forfeit: el motivo, si alguien perdió por incumplir las reglas. ``None`` si la
            partida acabó con normalidad.
    """

    winner: int
    moves: tuple[Move, ...]
    score: tuple[int, int]
    forfeit: str | None = None


def request_move(player: Mover, state: GameState) -> Move:
    """Le pide una jugada a un jugador y comprueba que es legal.

    Es la única definición de "un jugador incumple las reglas": lanzar una excepción o
    devolver algo que no es una jugada legal. El jugador recibe su propia copia del estado.

    Args:
        player: quien debe jugar.
        state: la posición, con el turno de ese jugador.

    Returns:
        La jugada, como una pareja ``(fila, columna)``.

    Raises:
        Forfeit: si el jugador lanza una excepción o devuelve una jugada ilegal.
    """
    try:
        move = player.choose_move(replace(state))
    except Exception as error:  # código ajeno: cualquier fallo es una derrota
        raise Forfeit(f"lanzó {type(error).__name__}: {error}") from error
    if not is_legal(state, move):
        raise Forfeit(f"devolvió una jugada ilegal: {move!r}")
    row, column = move
    return row, column


def play_game(
    player_a: Mover, player_b: Mover, state: GameState | None = None
) -> GameResult:
    """Juega una partida completa y devuelve el ganador y el historial de jugadas.

    Alterna los turnos, pide la jugada a quien le toca y repite hasta una posición
    terminal. El paso de turno lo gestiona el motor: a un jugador solo se le pide jugada
    cuando tiene alguna.

    Args:
        player_a: juega con las negras (el primero en mover desde la posición inicial).
        player_b: juega con las blancas.
        state: posición de partida. Por defecto, la inicial. Si es una posición a mitad
            de partida, se sigue desde ahí; si ya es terminal, devuelve el resultado sin
            pedir ninguna jugada.

    Returns:
        Un :class:`GameResult`. Si un jugador incumple las reglas (ver :func:`request_move`),
        pierde esa partida y el motivo queda en ``forfeit``.
    """
    state = initial_state() if state is None else state
    moves: list[Move] = []
    while not is_terminal(state):
        quien = state.player
        jugador = player_a if quien == BLACK else player_b
        try:
            jugada = request_move(jugador, state)
        except Forfeit as forfeit:
            return GameResult(
                winner=opponent(quien),
                moves=tuple(moves),
                score=score(state),
                forfeit=f"las {color_name(quien)} {forfeit.reason}",
            )
        moves.append(jugada)
        state = apply_move(state, jugada)
    return GameResult(winner(state) or 0, tuple(moves), score(state))
