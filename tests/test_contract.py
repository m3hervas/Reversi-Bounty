"""Prueba de contrato (tarea 2.4): todos los jugadores registrados cumplen las reglas.

La prueba se parametriza sobre el registro: añadir un bot nuevo a ``players/`` no exige
escribir otra prueba. Un bot correcto pasa solo; uno roto pone en rojo la integración continua.
"""

from __future__ import annotations

import pytest

from bots_rotos import BOTS_ROTOS
from contrato import verificar_contrato
from reversibounty import GameState, Move, Player, legal_moves
from reversibounty.manifest import load_players

REGISTRADOS = load_players()


@pytest.mark.parametrize("nombre", list(REGISTRADOS))
def test_cada_jugador_registrado_cumple_el_contrato(nombre):
    verificar_contrato(REGISTRADOS[nombre])


def test_hay_al_menos_un_jugador_registrado():
    assert REGISTRADOS


@pytest.mark.parametrize("roto", BOTS_ROTOS, ids=lambda cls: cls.__name__)
def test_un_bot_roto_incumple_el_contrato(roto):
    with pytest.raises(AssertionError):
        verificar_contrato(roto)


def test_un_bot_correcto_cumple_el_contrato_sin_pruebas_propias():
    class PrimeraJugada(Player):
        @classmethod
        def get_name(cls) -> str:
            return "primera"

        @classmethod
        def get_authors(cls) -> list[str]:
            return ["Tests"]

        @classmethod
        def get_description(cls) -> str:
            return "Siempre la primera jugada legal."

        @classmethod
        def get_icon(cls) -> str:
            return "1️⃣"

        def choose_move(self, state: GameState) -> Move:
            return legal_moves(state)[0]

    verificar_contrato(PrimeraJugada)


def test_el_mensaje_de_error_explica_que_hizo_mal_el_bot():
    from bots_rotos import JugadaIlegal

    with pytest.raises(AssertionError, match="jugadailegal.*ilegal"):
        verificar_contrato(JugadaIlegal)
