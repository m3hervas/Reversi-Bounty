"""El jugador aleatorio: el bot de referencia más sencillo posible.

Elige una casilla legal al azar, sin ninguna estrategia. Sirve de dos formas:

* Como **ejemplo** de cómo se escribe un bot: usa solo la API pública (``Player``,
  ``legal_moves``) y nada más.
* Como **vara de medir**: cualquier bot con algo de estrategia debería ganarle casi
  siempre. Si no lo hace, algo va mal.
"""

from __future__ import annotations

import random

from ..game import GameState, Move, legal_moves
from ..player import Player


class RandomPlayer(Player):
    """Juega una casilla legal elegida al azar."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    @classmethod
    def get_name(cls) -> str:
        return "aleatorio"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Reversi Bounty"]

    @classmethod
    def get_description(cls) -> str:
        return "Elige una casilla legal al azar. Sin estrategia: es la vara de medir del resto."

    @classmethod
    def get_icon(cls) -> str:
        return "🃏"

    @classmethod
    def create(cls, seed: int) -> RandomPlayer:
        """Con la misma semilla juega exactamente las mismas jugadas, para repetir partidas."""
        return cls(random.Random(seed))

    def choose_move(self, state: GameState) -> Move:
        return self._rng.choice(legal_moves(state))
