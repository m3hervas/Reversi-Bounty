"""Motor de Reversi (Othello) — la única fuente de verdad de las reglas.

Reglas implementadas:

* Tablero de 8x8. Empiezan las **negras**, con cuatro fichas en el centro.
* Una jugada coloca una ficha en una casilla vacía que **encierre** en línea recta
  (horizontal, vertical o diagonal) al menos una ficha rival entre la nueva ficha
  y otra propia. Todas las fichas encerradas se dan la vuelta.
* Si el jugador al que le toca no tiene jugadas legales, **pasa** automáticamente.
* La partida termina cuando ninguno de los dos puede mover. Gana quien tenga más
  fichas; si hay las mismas, es empate.

Decisiones de diseño:

* El estado es un :class:`GameState` **inmutable** (``frozen``). Ninguna función
  modifica sus argumentos: :func:`apply_move` devuelve un estado nuevo. Esto
  evita una fuente clásica de errores en minimax, que explora miles de futuros
  hipotéticos a partir del mismo estado.
* El estado es *hashable*, así que un bot puede usarlo como clave de una tabla
  de transposición sin hacer nada especial.
* El paso de turno es **automático**: a un jugador solo se le pide jugada cuando
  tiene alguna. Así el API de los bots no tiene que contemplar la jugada "pasar".
* El estado se convierte a/desde JSON con :meth:`GameState.to_dict` y
  :meth:`GameState.from_dict`, que es lo que usan la web y el torneo.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

#: Tamaño del tablero (8x8).
SIZE = 8

#: Valores de cada casilla.
EMPTY = 0
BLACK = 1
WHITE = -1

#: Un tablero es una tupla de filas; cada fila es una tupla de casillas.
Board = tuple[tuple[int, ...], ...]

#: Una jugada es ``(fila, columna)``, ambas entre 0 y 7.
Move = tuple[int, int]

#: Las 8 direcciones en las que se pueden encerrar fichas.
DIRECTIONS: tuple[tuple[int, int], ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
)


@dataclass(frozen=True)
class GameState:
    """Una posición de la partida: el tablero y el color al que le toca mover.

    Attributes:
        board: ``board[fila][columna]`` vale :data:`EMPTY`, :data:`BLACK` o
            :data:`WHITE`.
        player: color al que le toca mover (:data:`BLACK` o :data:`WHITE`). En
            una posición terminal no tiene significado.
    """

    board: Board
    player: int

    def to_dict(self) -> dict[str, Any]:
        """Devuelve el estado como un diccionario serializable a JSON.

        Returns:
            Un diccionario con las claves ``"board"`` (lista de 8 listas de 8 enteros) y
            ``"player"``.
        """
        return {"board": [list(row) for row in self.board], "player": self.player}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameState:
        """Construye un estado a partir de :meth:`to_dict`, validando su forma.

        Args:
            data: un diccionario con las claves ``"board"`` y ``"player"``.

        Returns:
            El estado correspondiente.

        Raises:
            ValueError: si el tablero no es 8x8, contiene valores no válidos o el
                jugador no es :data:`BLACK` ni :data:`WHITE`.
        """
        board = data.get("board")
        player = data.get("player")
        if not isinstance(board, (list, tuple)) or len(board) != SIZE:
            raise ValueError("board debe tener 8 filas")
        rows: list[tuple[int, ...]] = []
        for row in board:
            if not isinstance(row, (list, tuple)) or len(row) != SIZE:
                raise ValueError("cada fila debe tener 8 casillas")
            if any(cell not in (EMPTY, BLACK, WHITE) or isinstance(cell, bool) for cell in row):
                raise ValueError("las casillas solo pueden valer 0, 1 o -1")
            rows.append(tuple(row))
        if player not in (BLACK, WHITE) or isinstance(player, bool):
            raise ValueError("player debe ser 1 (negras) o -1 (blancas)")
        return cls(board=tuple(rows), player=player)

    def __str__(self) -> str:
        symbols = {EMPTY: ".", BLACK: "X", WHITE: "O"}
        lines = ["  a b c d e f g h"]
        for r, row in enumerate(self.board):
            lines.append(f"{r + 1} " + " ".join(symbols[c] for c in row))
        return "\n".join(lines)


def opponent(color: int) -> int:
    """Devuelve el color contrario.

    Args:
        color: :data:`BLACK` o :data:`WHITE`.

    Returns:
        :data:`WHITE` si ``color`` es :data:`BLACK`, y al revés.
    """
    return -color


def initial_state() -> GameState:
    """Devuelve la posición inicial estándar: cuatro fichas en el centro, mueven negras.

    Returns:
        Un estado nuevo con dos fichas negras, dos blancas y el turno de las negras.
    """
    board = [[EMPTY] * SIZE for _ in range(SIZE)]
    mid = SIZE // 2
    board[mid - 1][mid - 1] = WHITE
    board[mid][mid] = WHITE
    board[mid - 1][mid] = BLACK
    board[mid][mid - 1] = BLACK
    return GameState(board=tuple(tuple(row) for row in board), player=BLACK)


def _on_board(row: int, col: int) -> bool:
    return 0 <= row < SIZE and 0 <= col < SIZE


def flips(board: Board, color: int, move: Move) -> list[Move]:
    """Devuelve las fichas que se darían la vuelta si ``color`` jugase en ``move``.

    Trabaja con un tablero y un color (no con un :class:`GameState`) porque solo mira
    la geometría y no necesita saber de quién es el turno: así sirve también para
    preguntar qué pasaría si jugase el otro color.

    Args:
        board: el tablero, sin modificar.
        color: :data:`BLACK` o :data:`WHITE`, quien jugaría.
        move: la casilla ``(fila, columna)`` donde se pondría la ficha.

    Returns:
        Las casillas ``(fila, columna)`` que se voltearían. Una lista vacía significa que
        la jugada no es legal para ese color.
    """
    row, col = move
    if not _on_board(row, col) or board[row][col] != EMPTY:
        return []
    other = opponent(color)
    flipped: list[Move] = []
    for dr, dc in DIRECTIONS:
        r, c = row + dr, col + dc
        line: list[Move] = []
        while _on_board(r, c) and board[r][c] == other:
            line.append((r, c))
            r += dr
            c += dc
        if line and _on_board(r, c) and board[r][c] == color:
            flipped.extend(line)
    return flipped


def _iter_moves(board: Board, color: int) -> Iterator[Move]:
    """Jugadas legales de ``color`` en ``board``, por fila y columna (interno, perezoso)."""
    return (
        (r, c)
        for r in range(SIZE)
        for c in range(SIZE)
        if board[r][c] == EMPTY and flips(board, color, (r, c))
    )


def _has_moves(board: Board, color: int) -> bool:
    """Indica si ``color`` tiene alguna jugada legal. Se detiene en cuanto encuentra una."""
    return next(_iter_moves(board, color), None) is not None


def legal_moves(state: GameState) -> list[Move]:
    """Devuelve las jugadas legales del jugador al que le toca.

    Args:
        state: la posición actual, sin modificar.

    Returns:
        Las jugadas ``(fila, columna)`` ordenadas por fila y columna. Vacía si el jugador
        no puede mover (porque pasa o porque la partida ha terminado).
    """
    return list(_iter_moves(state.board, state.player))


def _as_move(move: object) -> Move | None:
    """Convierte ``move`` en ``(fila, columna)`` si es una pareja de enteros; si no, ``None``."""
    if not isinstance(move, (tuple, list)) or len(move) != 2:
        return None
    row, col = move
    if not isinstance(row, int) or not isinstance(col, int):
        return None
    if isinstance(row, bool) or isinstance(col, bool):
        return None
    return row, col


def is_legal(state: GameState, move: object) -> bool:
    """Indica si ``move`` es una jugada legal en ``state``.

    ``move`` se tipa como ``object`` a propósito: sirve para juzgar lo que
    devuelve un bot **no fiable**, que puede ser cualquier cosa.

    Args:
        state: la posición actual.
        move: lo que se quiere comprobar; normalmente ``(fila, columna)``, pero puede ser
            cualquier objeto.

    Returns:
        ``True`` solo si ``move`` es una pareja de enteros que forma una jugada legal.
        Nunca lanza una excepción, sea cual sea ``move``.
    """
    parsed = _as_move(move)
    return parsed is not None and bool(flips(state.board, state.player, parsed))


def apply_move(state: GameState, move: Move) -> GameState:
    """Devuelve el estado resultante de jugar ``move``. No modifica ``state``.

    Gestiona el paso de turno: si el rival no tiene jugadas pero el jugador
    actual sí, el turno vuelve al jugador actual.

    Args:
        state: la posición actual; nunca se modifica.
        move: la jugada ``(fila, columna)`` a aplicar.

    Returns:
        Un estado nuevo, con la ficha colocada, las fichas encerradas volteadas y el
        turno ya actualizado.

    Raises:
        ValueError: si la jugada no es legal.
    """
    parsed = _as_move(move)
    to_flip = flips(state.board, state.player, parsed) if parsed is not None else []
    if parsed is None or not to_flip:
        raise ValueError(f"Jugada ilegal {move!r} para {color_name(state.player)}")
    row, col = parsed
    board = [list(r) for r in state.board]
    board[row][col] = state.player
    for r, c in to_flip:
        board[r][c] = state.player
    new_board = tuple(tuple(r) for r in board)

    next_player = opponent(state.player)
    if not _has_moves(new_board, next_player) and _has_moves(new_board, state.player):
        next_player = state.player  # el rival pasa
    return GameState(board=new_board, player=next_player)


def is_terminal(state: GameState) -> bool:
    """Indica si la partida ha terminado (ninguno de los dos puede mover).

    Args:
        state: la posición a comprobar.

    Returns:
        ``True`` si ni las negras ni las blancas tienen ninguna jugada legal.
    """
    return not _has_moves(state.board, BLACK) and not _has_moves(state.board, WHITE)


def score(state: GameState) -> tuple[int, int]:
    """Cuenta las fichas de cada color.

    Args:
        state: la posición a contar.

    Returns:
        Una pareja ``(fichas_negras, fichas_blancas)``.
    """
    black = sum(row.count(BLACK) for row in state.board)
    white = sum(row.count(WHITE) for row in state.board)
    return black, white


def winner(state: GameState) -> int | None:
    """Devuelve el ganador de una posición terminal.

    Args:
        state: la posición a evaluar.

    Returns:
        :data:`BLACK`, :data:`WHITE`, ``0`` si es empate, o ``None`` si la
        partida todavía no ha terminado.
    """
    if not is_terminal(state):
        return None
    black, white = score(state)
    if black > white:
        return BLACK
    if white > black:
        return WHITE
    return 0


def color_name(color: int) -> str:
    """Nombre legible de un color.

    Args:
        color: :data:`BLACK` o :data:`WHITE`.

    Returns:
        ``"negras"`` o ``"blancas"``.
    """
    return "negras" if color == BLACK else "blancas"


def move_to_str(move: Move) -> str:
    """Convierte ``(fila, columna)`` a notación estándar, p. ej. ``(2, 3)`` → ``"d3"``.

    Args:
        move: una casilla ``(fila, columna)``, ambas entre 0 y 7.

    Returns:
        El texto de la casilla: una letra de la ``a`` a la ``h`` y un número del 1 al 8.
    """
    row, col = move
    return f"{'abcdefgh'[col]}{row + 1}"


def str_to_move(text: str) -> Move:
    """Convierte notación estándar a ``(fila, columna)``, p. ej. ``"d3"`` → ``(2, 3)``.

    Args:
        text: la casilla escrita, como ``"d3"``. Admite mayúsculas y espacios alrededor.

    Returns:
        La casilla como pareja ``(fila, columna)``.

    Raises:
        ValueError: si el texto no es una casilla válida.
    """
    text = text.strip().lower()
    if len(text) != 2 or text[0] not in "abcdefgh" or text[1] not in "12345678":
        raise ValueError(f"Casilla no válida: {text!r}")
    return int(text[1]) - 1, "abcdefgh".index(text[0])
