"""El ejecutor de partidas: juega una partida completa entre dos jugadores.

``play_game`` no sabe nada de personas, bots, dificultades ni torneos. Solo necesita dos
objetos con un método ``choose_move``, que es justo lo que ofrece
:class:`~reversibounty.player.Player`.
Así el mismo ejecutor sirve para el torneo, la web y los tests.

Decisiones de diseño:

* **Valida todas las jugadas antes de aplicarlas.** Un bot no es de fiar: puede devolver
  una casilla ocupada, ``None``, un texto o lanzar una excepción. Nada de eso llega al
  motor: el ejecutor lo juzga con :func:`~reversibounty.game.is_legal`.
* **Quien incumple, pierde esa partida** y la partida se da por terminada con el motivo
  anotado, en lugar de romper todo el programa. Así un bot malo no puede estropear ni un
  torneo ni a los demás jugadores. La guía no fija qué hacer aquí; esta es nuestra decisión.
* **Cada jugador recibe su propio objeto de estado.** Como :class:`~reversibounty.game.GameState`
  es inmutable, un bot que intente modificarlo no puede: se queja con una excepción y solo
  se perjudica a sí mismo.
* **El ejecutor no pone límites de tiempo.** Eso corresponde al torneo (paso 5.2).
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
        Un :class:`GameResult`. Si un jugador lanza una excepción o devuelve una jugada
        ilegal, pierde esa partida y el motivo queda en ``forfeit``.
    """
    state = initial_state() if state is None else state
    moves: list[Move] = []
    while not is_terminal(state):
        quien = state.player
        jugador = player_a if quien == BLACK else player_b
        try:
            jugada = jugador.choose_move(replace(state))  # copia: cada bot recibe la suya
        except Exception as error:  # código ajeno: cualquier fallo es una derrota
            motivo = f"lanzó {type(error).__name__}: {error}"
            return _pierde(quien, state, moves, motivo)
        if not is_legal(state, jugada):
            return _pierde(quien, state, moves, f"devolvió una jugada ilegal: {jugada!r}")
        fila, columna = jugada
        moves.append((fila, columna))
        state = apply_move(state, jugada)
    return GameResult(winner(state) or 0, tuple(moves), score(state))


def _pierde(quien: int, state: GameState, moves: list[Move], motivo: str) -> GameResult:
    """Resultado de una partida en la que ``quien`` pierde por incumplir las reglas."""
    return GameResult(
        winner=opponent(quien),
        moves=tuple(moves),
        score=score(state),
        forfeit=f"las {color_name(quien)} {motivo}",
    )
