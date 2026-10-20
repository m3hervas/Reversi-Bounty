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
        """Devuelve el estado como un diccionario serializable a JSON."""
        return {"board": [list(row) for row in self.board], "player": self.player}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameState:
        """Construye un estado a partir de :meth:`to_dict`, validando su forma.

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
    """Devuelve el color contrario."""
    return -color


def initial_state() -> GameState:
    """Devuelve la posición inicial estándar: cuatro fichas en el centro, mueven negras."""
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

    No comprueba de quién es el turno; solo la geometría. Una lista vacía
    significa que la jugada no es legal para ese color.
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


def moves_for(board: Board, color: int) -> list[Move]:
    """Devuelve las jugadas legales de ``color`` en ``board``, ordenadas por fila y columna."""
    return [
        (r, c)
        for r in range(SIZE)
        for c in range(SIZE)
        if board[r][c] == EMPTY and flips(board, color, (r, c))
    ]


def legal_moves(state: GameState) -> list[Move]:
    """Devuelve las jugadas legales del jugador al que le toca. Vacía si la partida acabó."""
    return moves_for(state.board, state.player)


def is_legal(state: GameState, move: object) -> bool:
    """Indica si ``move`` es una jugada legal en ``state``.

    ``move`` se tipa como ``object`` a propósito: sirve para juzgar lo que
    devuelve un bot **no fiable**, que puede ser cualquier cosa.
    """
    if not isinstance(move, (tuple, list)) or len(move) != 2:
        return False
    row, col = move
    if not isinstance(row, int) or not isinstance(col, int):
        return False
    if isinstance(row, bool) or isinstance(col, bool):
        return False
    return bool(flips(state.board, state.player, (row, col)))


def apply_move(state: GameState, move: Move) -> GameState:
    """Devuelve el estado resultante de jugar ``move``. No modifica ``state``.

    Gestiona el paso de turno: si el rival no tiene jugadas pero el jugador
    actual sí, el turno vuelve al jugador actual.

    Raises:
        ValueError: si la jugada no es legal.
    """
    if not is_legal(state, move):
        raise ValueError(f"Jugada ilegal {move!r} para {color_name(state.player)}")
    row, col = move
    to_flip = flips(state.board, state.player, (row, col))
    board = [list(r) for r in state.board]
    board[row][col] = state.player
    for r, c in to_flip:
        board[r][c] = state.player
    new_board = tuple(tuple(r) for r in board)

    next_player = opponent(state.player)
    if not moves_for(new_board, next_player) and moves_for(new_board, state.player):
        next_player = state.player  # el rival pasa
    return GameState(board=new_board, player=next_player)


def is_terminal(state: GameState) -> bool:
    """Indica si la partida ha terminado (ninguno de los dos puede mover)."""
    return not moves_for(state.board, BLACK) and not moves_for(state.board, WHITE)


def score(state: GameState) -> tuple[int, int]:
    """Devuelve ``(fichas_negras, fichas_blancas)``."""
    black = sum(row.count(BLACK) for row in state.board)
    white = sum(row.count(WHITE) for row in state.board)
    return black, white


def winner(state: GameState) -> int | None:
    """Devuelve el ganador de una posición terminal.

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
    """Nombre legible de un color: ``"negras"`` o ``"blancas"``."""
    return "negras" if color == BLACK else "blancas"


def move_to_str(move: Move) -> str:
    """Convierte ``(fila, columna)`` a notación estándar, p. ej. ``(2, 3)`` → ``"d3"``."""
    row, col = move
    return f"{'abcdefgh'[col]}{row + 1}"


def str_to_move(text: str) -> Move:
    """Convierte notación estándar a ``(fila, columna)``, p. ej. ``"d3"`` → ``(2, 3)``.

    Raises:
        ValueError: si el texto no es una casilla válida.
    """
    text = text.strip().lower()
    if len(text) != 2 or text[0] not in "abcdefgh" or text[1] not in "12345678":
        raise ValueError(f"Casilla no válida: {text!r}")
    return int(text[1]) - 1, "abcdefgh".index(text[0])
