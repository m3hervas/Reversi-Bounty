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
    color_name,
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
from .match import GameResult, play_game
from .player import Player

__version__ = "0.1.0"

__all__ = [
    "BLACK",
    "EMPTY",
    "SIZE",
    "WHITE",
    "Board",
    "GameResult",
    "GameState",
    "Move",
    "Player",
    "__version__",
    "apply_move",
    "color_name",
    "flips",
    "initial_state",
    "is_legal",
    "is_terminal",
    "legal_moves",
    "move_to_str",
    "opponent",
    "play_game",
    "score",
    "str_to_move",
    "winner",
]
