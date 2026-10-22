"""Jugadores de referencia incluidos con el proyecto."""

from .greedy_player import GreedyPlayer
from .random_player import RandomPlayer
from .zeff_minmax import ZeffMinmaxPlayer

__all__ = ["GreedyPlayer", "RandomPlayer", "ZeffMinmaxPlayer"]
