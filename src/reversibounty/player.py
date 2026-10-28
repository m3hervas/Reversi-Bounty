"""La API de jugadores: lo único que necesita conocer quien escribe un bot.

Un bot es una subclase de :class:`Player` que declara **quién es** (nombre, autores,
descripción y un emoji) e implementa **un único método de juego**,
:meth:`Player.choose_move`. No hace falta tocar el código del juego.

Ejemplo mínimo::

    import random
    from reversibounty import GameState, Move, Player, legal_moves

    class MiBot(Player):
        @classmethod
        def get_name(cls) -> str:
            return "Mi bot"

        @classmethod
        def get_authors(cls) -> list[str]:
            return ["Tu Nombre"]

        @classmethod
        def get_description(cls) -> str:
            return "Juega una casilla legal al azar."

        @classmethod
        def get_icon(cls) -> str:
            return "🎲"

        def choose_move(self, state: GameState) -> Move:
            return random.choice(legal_moves(state))

Qué ve un jugador: el Reversi es un juego de **información perfecta** (los dos ven el
tablero completo y no hay azar), así que el bot recibe el :class:`~reversibounty.game.GameState`
entero.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .game import GameState, Move


class Player(ABC):
    """Un jugador de Reversi.

    Hay que implementar :meth:`get_name`, :meth:`get_authors`, :meth:`get_description`,
    :meth:`get_icon` y :meth:`choose_move`. Si falta alguno, Python se niega a crear el
    jugador.
    """

    # -- Identidad: se puede leer sin construir el jugador -------------------- #

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Nombre único y legible del jugador. Se mostrará en la clasificación.

        Es un nombre propio, así que **siempre empieza por mayúscula**: ``"Buggy aleatorio"``,
        ``"Esquinero"``, ``"Mi bot"``.
        """

    @classmethod
    @abstractmethod
    def get_authors(cls) -> list[str]:
        """Lista no vacía con los autores del jugador."""

    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """Una frase que describa la *estrategia* del jugador."""

    @classmethod
    @abstractmethod
    def get_icon(cls) -> str:
        """Un único emoji que acompaña al nombre del jugador en la clasificación."""

    # -- Construcción ------------------------------------------------------- #

    @classmethod
    def create(cls, seed: int) -> Player:
        """Crea un jugador para una partida, con una semilla.

        Es la forma en que el árbitro y el torneo construyen los jugadores. La semilla
        sirve para que un bot que usa azar se pueda **repetir**: con la misma semilla,
        las mismas decisiones. La versión por defecto ignora la semilla y llama a
        ``cls()``. Sobrescríbela si tu bot usa azar::

            @classmethod
            def create(cls, seed: int) -> "MiBot":
                return cls(random.Random(seed))
        """
        return cls()

    # -- Juego -------------------------------------------------------------- #

    @abstractmethod
    def choose_move(self, state: GameState) -> Move:
        """Elige una jugada.

        Solo se llama cuando hay al menos una jugada legal. El color con el que
        juegas es ``state.player``.

        Args:
            state: la posición actual, completa. Es inmutable: no puedes estropearla.

        Returns:
            ``(fila, columna)``, ambas entre 0 y 7. La jugada **debe** ser legal: una
            jugada ilegal, una excepción o pasarse de tiempo hace perder la partida.
        """
