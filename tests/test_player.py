"""Tests de la interfaz Player: que sea fácil de implementar y difícil de implementar mal."""

from __future__ import annotations

import random

import pytest

from reversibounty import GameState, Move, Player, initial_state, is_legal, legal_moves


class BotAleatorio(Player):
    """Bot completo y mínimo, usado como ejemplo de subclase correcta."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    @classmethod
    def get_name(cls) -> str:
        return "bot-aleatorio"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Equipo"]

    @classmethod
    def get_description(cls) -> str:
        return "Juega una casilla legal al azar."

    @classmethod
    def get_icon(cls) -> str:
        return "🎲"

    @classmethod
    def create(cls, seed: int) -> BotAleatorio:
        return cls(random.Random(seed))

    def choose_move(self, state: GameState) -> Move:
        return self.rng.choice(legal_moves(state))


def test_player_abstracta_no_se_puede_instanciar():
    with pytest.raises(TypeError):
        Player()  # type: ignore[abstract]


def test_subclase_sin_choose_move_no_se_puede_instanciar():
    class SinJugada(Player):
        @classmethod
        def get_name(cls) -> str:
            return "sin-jugada"

        @classmethod
        def get_authors(cls) -> list[str]:
            return ["Equipo"]

        @classmethod
        def get_description(cls) -> str:
            return "Le falta choose_move."

        @classmethod
        def get_icon(cls) -> str:
            return "🎲"

    with pytest.raises(TypeError, match="choose_move"):
        SinJugada()  # type: ignore[abstract]


@pytest.mark.parametrize("falta", ["get_name", "get_authors", "get_description", "get_icon"])
def test_subclase_sin_identidad_no_se_puede_instanciar(falta):
    metodos = {
        "get_name": classmethod(lambda cls: "x"),
        "get_authors": classmethod(lambda cls: ["x"]),
        "get_description": classmethod(lambda cls: "x"),
        "get_icon": classmethod(lambda cls: "🎲"),
        "choose_move": lambda self, state: (2, 3),
    }
    del metodos[falta]
    Incompleta = type("Incompleta", (Player,), metodos)
    with pytest.raises(TypeError, match=falta):
        Incompleta()


def test_subclase_completa_se_puede_instanciar():
    assert isinstance(BotAleatorio(), Player)


def test_la_identidad_se_lee_sin_construir_el_jugador():
    assert BotAleatorio.get_name() == "bot-aleatorio"
    assert BotAleatorio.get_authors() == ["Equipo"]
    assert BotAleatorio.get_description() == "Juega una casilla legal al azar."


def test_el_icono_es_obligatorio_y_se_lee_sin_construir_el_jugador():
    assert BotAleatorio.get_icon() == "🎲"


def test_create_por_defecto_devuelve_una_instancia_e_ignora_la_semilla():
    class Simple(Player):
        @classmethod
        def get_name(cls) -> str:
            return "simple"

        @classmethod
        def get_authors(cls) -> list[str]:
            return ["Equipo"]

        @classmethod
        def get_description(cls) -> str:
            return "Siempre la primera jugada legal."

        @classmethod
        def get_icon(cls) -> str:
            return "1️⃣"

        def choose_move(self, state: GameState) -> Move:
            return legal_moves(state)[0]

    assert isinstance(Simple.create(seed=123), Simple)


def test_create_con_la_misma_semilla_da_las_mismas_decisiones():
    estado = initial_state()
    a = [BotAleatorio.create(seed=7).choose_move(estado) for _ in range(5)]
    b = [BotAleatorio.create(seed=7).choose_move(estado) for _ in range(5)]
    assert a == b


def test_create_con_otra_semilla_puede_dar_otras_decisiones():
    estado = initial_state()
    jugadas = {BotAleatorio.create(seed=s).choose_move(estado) for s in range(30)}
    assert len(jugadas) > 1


def test_choose_move_recibe_el_estado_completo_y_devuelve_una_jugada_legal():
    estado = initial_state()
    jugada = BotAleatorio.create(seed=0).choose_move(estado)
    assert is_legal(estado, jugada)
