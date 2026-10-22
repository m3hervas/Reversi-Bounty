"""Jugadores rotos a propósito, para comprobar que el contrato los detecta.

Todos tienen una identidad válida (así pasan la lista de jugadores) y todos incumplen el
contrato al jugar. Los dos primeros usan solo la API pública; los demás hacen cosas que un
bot de fuera podría hacer por error o por trampa.
"""

from __future__ import annotations

import sys
import time

from reversibounty import GameState, Move, Player, legal_moves


class _Base(Player):
    """Identidad común: lo único que cambia entre los bots rotos es ``choose_move``."""

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__.lower()

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Tests"]

    @classmethod
    def get_description(cls) -> str:
        return "Bot roto a propósito para comprobar el contrato."

    @classmethod
    def get_icon(cls) -> str:
        return "💥"


class LanzaExcepcion(_Base):
    """Falla con una excepción en su primera jugada."""

    def choose_move(self, state: GameState) -> Move:
        raise RuntimeError("fallo en choose_move")


class JugadaIlegal(_Base):
    """Devuelve siempre una casilla ocupada: nunca puede ser una jugada legal."""

    def choose_move(self, state: GameState) -> Move:
        return (3, 3)  # una de las cuatro fichas del centro, ocupada desde el principio


class NoDevuelveNada(_Base):
    """Se olvida de devolver la jugada."""

    def choose_move(self, state: GameState) -> Move:
        return None  # type: ignore[return-value]


class ModificaElEstado(_Base):
    """Intenta cambiar el estado que recibe y, si pudiera, juega bien."""

    def choose_move(self, state: GameState) -> Move:
        state.player = -state.player  # type: ignore[misc]
        return legal_moves(state)[0]


class ModificaElTablero(_Base):
    """Intenta cambiar una casilla del tablero que recibe."""

    def choose_move(self, state: GameState) -> Move:
        state.board[3][3] = 0  # type: ignore[index]
        return legal_moves(state)[0]


BOTS_ROTOS = [LanzaExcepcion, JugadaIlegal, NoDevuelveNada, ModificaElEstado, ModificaElTablero]


# -- Rotos que solo el torneo puede contener --------------------------------- #
# No están en BOTS_ROTOS, que también usan la prueba de contrato y la web sin la capa de
# protección del torneo: SeCuelga las dejaría colgadas, SaleDelPrograma cerraría pytest,
# CambiaDeNombre juega bien y ModificaAEscondidas juega una jugada legal, así que play_game
# no ve nada raro.


class ModificaAEscondidas(_Base):
    """Se salta el ``frozen`` del estado con ``object.__setattr__`` y juega una jugada legal."""

    def choose_move(self, state: GameState) -> Move:
        jugada = legal_moves(state)[0]
        object.__setattr__(state, "player", -state.player)
        return jugada


class SeCuelga(_Base):
    """No devuelve nunca la jugada: se queda bloqueado."""

    def choose_move(self, state: GameState) -> Move:
        time.sleep(3600)
        return legal_moves(state)[0]


class SaleDelPrograma(_Base):
    """Intenta cerrar el programa entero con ``sys.exit()``."""

    def choose_move(self, state: GameState) -> Move:
        sys.exit("adiós")


class CambiaDeNombre(_Base):
    """Juega bien, pero su nombre cambia cuando se toca ``NOMBRE``: miente sobre quién es."""

    NOMBRE = "cambiadenombre"

    @classmethod
    def get_name(cls) -> str:
        return cls.NOMBRE

    def choose_move(self, state: GameState) -> Move:
        return legal_moves(state)[0]
