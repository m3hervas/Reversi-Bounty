"""Reversi Bounty: motor de Reversi, API de bots y torneo automático."""

from .game import (
    BLACK,
    EMPTY,
    SIZE,
    WHITE,
    Board,
    GameState,
    Move,
    apply_move,
    flips,
    initial_state,
    is_legal,
    is_terminal,
    legal_moves,
    move_to_str,
    opponent,
    score,
    str_to_move,
    winner,
)

__version__ = "0.1.0"

__all__ = [
    "BLACK",
    "EMPTY",
    "SIZE",
    "WHITE",
    "Board",
    "GameState",
    "Move",
    "apply_move",
    "flips",
    "initial_state",
    "is_legal",
    "is_terminal",
    "legal_moves",
    "move_to_str",
    "opponent",
    "score",
    "str_to_move",
    "winner",
]
