"""La comprobación del contrato de un jugador: legalidad de cada jugada y estado intacto.

Se usa en los tests con todos los jugadores registrados, de modo que añadir un bot nuevo no
exige escribir ninguna prueba nueva: si hace una jugada ilegal, falla, o modifica el estado
que recibe, el test de integración continua se pone en rojo.
"""

from __future__ import annotations

from reversibounty import BLACK, WHITE, GameState, Move, Player, is_legal, play_game
from reversibounty.bots import RandomPlayer


class Vigilante:
    """Envuelve a un jugador y anota, en cada turno, si incumplió el contrato.

    No lanza excepciones: guarda los problemas para que quien lo use los compruebe al final.
    Así se ve todo lo que hizo mal y no solo lo primero.
    """

    def __init__(self, jugador: Player) -> None:
        self.jugador = jugador
        self.turnos = 0
        self.problemas: list[str] = []

    def choose_move(self, state: GameState) -> Move:
        antes = state.to_dict()
        jugada = self.jugador.choose_move(state)
        self.turnos += 1
        if state.to_dict() != antes:
            self.problemas.append(f"turno {self.turnos}: modificó el estado que recibió")
        if not is_legal(state, jugada):
            self.problemas.append(f"turno {self.turnos}: jugada ilegal {jugada!r}")
        return jugada


def verificar_contrato(clase: type[Player], semillas: tuple[int, ...] = (0, 1, 2)) -> None:
    """Juega varias partidas con el jugador, con negras y con blancas, y comprueba el contrato.

    Contra un :class:`~reversibounty.bots.RandomPlayer`, en cada turno comprueba que la
    jugada es legal y que el jugador no modifica el estado que recibe.

    Args:
        clase: la clase del jugador.
        semillas: una partida (con cada color) por semilla.

    Raises:
        AssertionError: con el detalle de lo que hizo mal, si incumple el contrato.
    """
    nombre = clase.get_name()
    assert nombre[:1].isupper(), f"{nombre!r}: el nombre de un bot empieza siempre por mayúscula"
    for semilla in semillas:
        for color in (BLACK, WHITE):
            vigilado = Vigilante(clase.create(semilla))
            rival = RandomPlayer.create(semilla + 1000)
            a, b = (vigilado, rival) if color == BLACK else (rival, vigilado)
            resultado = play_game(a, b)
            lado = "negras" if color == BLACK else "blancas"
            donde = f"{nombre} ({lado}, semilla {semilla})"
            assert resultado.forfeit is None, f"{donde}: {resultado.forfeit}"
            assert not vigilado.problemas, f"{donde}: {vigilado.problemas}"
            assert vigilado.turnos > 0, f"{donde}: no jugó ningún turno"
