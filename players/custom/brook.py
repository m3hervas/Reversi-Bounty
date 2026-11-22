"""Brook silencioso: juega "callado" (pocas fichas, rival sin opciones) y solo al final va a por fichas.

Es lo contrario del voraz: en Reversi, tener muchas fichas pronto suele ser malo, porque cada
ficha que das la vuelta es una ficha que el rival puede volver a voltear y le abre jugadas.
Por eso Brook, en cada turno, prueba todas sus jugadas legales con ``apply_move`` y elige así:

1. **Esquina** si puede: una ficha en la esquina ya no se puede voltear nunca.
2. **Nunca regala esquinas**: evita las casillas pegadas a una esquina vacía (X y C), salvo
   que no le quede otra, y castiga mucho cualquier jugada tras la que el rival pueda tomar
   una esquina.
3. **Jugada silenciosa**: entre las demás, la que deja al rival con **menos jugadas**, a él
   con **más jugadas** y con **menos fichas expuestas** (las que tocan una casilla vacía, la
   "frontera", que son las que el rival puede voltear).
4. **Final**: con 10 casillas vacías o menos cambia de idea y juega la que le deja con más
   fichas, porque al terminar solo cuenta quién tiene más.

No mira más de una jugada hacia delante. Los empates se deshacen al azar con su semilla.
"""

from __future__ import annotations

import random

from reversibounty import EMPTY, SIZE, GameState, Move, Player, apply_move, legal_moves

ESQUINAS = {(0, 0), (0, SIZE - 1), (SIZE - 1, 0), (SIZE - 1, SIZE - 1)}
#: Cada esquina con las tres casillas que la rodean (la X en diagonal y las dos C al lado).
VECINAS_DE_ESQUINA = {
    (0, 0): {(0, 1), (1, 0), (1, 1)},
    (0, SIZE - 1): {(0, SIZE - 2), (1, SIZE - 1), (1, SIZE - 2)},
    (SIZE - 1, 0): {(SIZE - 2, 0), (SIZE - 1, 1), (SIZE - 2, 1)},
    (SIZE - 1, SIZE - 1): {(SIZE - 2, SIZE - 1), (SIZE - 1, SIZE - 2), (SIZE - 2, SIZE - 2)},
}
#: Casillas vacías a partir de las que deja de jugar callado y va a por fichas.
VACIAS_FINAL = 10
DIRECCIONES = [(df, dc) for df in (-1, 0, 1) for dc in (-1, 0, 1) if (df, dc) != (0, 0)]


def vacias(state: GameState) -> int:
    return sum(fila.count(EMPTY) for fila in state.board)


def fichas(state: GameState, color: int) -> int:
    return sum(fila.count(color) for fila in state.board)


def frontera(state: GameState, color: int) -> int:
    """Fichas de ``color`` que tocan alguna casilla vacía: las que el rival puede voltear."""
    tablero = state.board
    total = 0
    for f in range(SIZE):
        for c in range(SIZE):
            if tablero[f][c] != color:
                continue
            for df, dc in DIRECCIONES:
                nf, nc = f + df, c + dc
                if 0 <= nf < SIZE and 0 <= nc < SIZE and tablero[nf][nc] == EMPTY:
                    total += 1
                    break
    return total


def mis_jugadas(despues: GameState, yo: int) -> int:
    """Jugadas que tendría yo en esta posición si me tocara (mi "movilidad")."""
    if despues.player == yo:
        return len(legal_moves(despues))
    return len(legal_moves(GameState(board=despues.board, player=yo)))


class BrookSilencioso(Player):
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    @classmethod
    def get_name(cls) -> str:
        return "Brook silencioso"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Equipo CONECTA_CUATRO"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Juega callado: pocas fichas expuestas y el rival sin opciones; toma esquinas, "
            "nunca las regala y solo al final va a por el mayor número de fichas."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🎻"

    @classmethod
    def create(cls, seed: int) -> BrookSilencioso:
        return cls(random.Random(seed))

    def choose_move(self, state: GameState) -> Move:
        jugadas = legal_moves(state)
        yo = state.player

        esquinas = [j for j in jugadas if j in ESQUINAS]
        if esquinas:
            return self._rng.choice(esquinas)

        peligrosas = {
            casilla
            for esquina, vecinas in VECINAS_DE_ESQUINA.items()
            if state.board[esquina[0]][esquina[1]] == EMPTY
            for casilla in vecinas
        }
        candidatas = [j for j in jugadas if j not in peligrosas] or jugadas

        final = vacias(state) <= VACIAS_FINAL
        puntos: dict[Move, int] = {}
        for jugada in candidatas:
            despues = apply_move(state, jugada)
            if final:
                puntos[jugada] = fichas(despues, yo)
                continue
            rival = [] if despues.player == yo else legal_moves(despues)
            regala = any(j in ESQUINAS for j in rival)
            puntos[jugada] = (
                -50 * regala  # le deja una esquina al rival
                - 3 * len(rival)  # rival con pocas opciones
                + mis_jugadas(despues, yo)  # yo con muchas
                - frontera(despues, yo)  # pocas fichas expuestas
            )
        mejor = max(puntos.values())
        return self._rng.choice([j for j, p in puntos.items() if p == mejor])
