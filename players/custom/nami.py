"""Nami navegante: alfa-beta con profundización iterativa sobre un tablero en bits.

* El tablero son dos enteros de 64 bits (mis fichas ``p`` y las del rival ``o``); la casilla
  ``(fila, columna)`` es el bit ``fila * 8 + columna``.
* Busca a profundidad 1, 2, 3... hasta gastar su tiempo y juega la mejor jugada de la última
  profundidad completa. Si llega al número de casillas vacías, el resultado es exacto.
* Evalúa esquinas, casillas X/C (solo con la esquina vacía), movilidad y, al final, fichas.
"""

from __future__ import annotations

import time

from reversibounty import GameState, Move, Player, legal_moves

TIEMPO = 0.5  # segundos por jugada (el torneo da 1 s)
LLENO = (1 << 64) - 1
SIN_A, SIN_H = 0xFEFEFEFEFEFEFEFE, 0x7F7F7F7F7F7F7F7F
# (desplazamiento, máscara hacia la izquierda, máscara hacia la derecha): evitan saltar de borde.
DIRS = ((1, SIN_A, SIN_H), (8, LLENO, LLENO), (9, SIN_A, SIN_H), (7, SIN_H, SIN_A))
ESQUINAS = 0x8100000000000081
BORDES = 0x3C0081818181003C  # bordes sin esquinas ni casillas C
# Cada esquina con su casilla X (diagonal) y sus dos casillas C (al lado).
RINCONES = ((1 << 0, 1 << 9, 1 << 1 | 1 << 8), (1 << 7, 1 << 14, 1 << 6 | 1 << 15),
            (1 << 56, 1 << 49, 1 << 57 | 1 << 48), (1 << 63, 1 << 54, 1 << 62 | 1 << 55))
GANAR = 10_000


def jugadas(p: int, o: int) -> int:
    """Máscara con las jugadas legales de ``p``."""
    res = 0
    for s, ml, mr in DIRS:
        t = o & ml & (p << s)
        for _ in range(5):
            t |= o & ml & (t << s)
        res |= ml & (t << s)
        t = o & mr & (p >> s)
        for _ in range(5):
            t |= o & mr & (t >> s)
        res |= mr & (t >> s)
    return res & ~(p | o) & LLENO


def volteos(p: int, o: int, m: int) -> int:
    """Fichas de ``o`` que se voltean si ``p`` juega en el bit ``m``."""
    total = 0
    for s, ml, mr in DIRS:
        linea, x = 0, (m << s) & ml
        while x & o:
            linea, x = linea | x, (x << s) & ml
        if x & p:
            total |= linea
        linea, x = 0, (m >> s) & mr
        while x & o:
            linea, x = linea | x, (x >> s) & mr
        if x & p:
            total |= linea
    return total


def evaluar(p: int, o: int) -> int:
    """Valor de la posición para ``p`` (quien mueve)."""
    def cuenta(mascara: int) -> int:
        return (p & mascara).bit_count() - (o & mascara).bit_count()

    valor = 100 * cuenta(ESQUINAS) + 10 * cuenta(BORDES)
    for esquina, x, c in RINCONES:
        if not (p | o) & esquina:
            valor -= 40 * cuenta(x) + 15 * cuenta(c)
    mias, suyas = jugadas(p, o).bit_count(), jugadas(o, p).bit_count()
    valor += 80 * (mias - suyas) // (mias + suyas + 2)
    # Frontera: mis fichas pegadas a casillas vacías son puertas de entrada para el rival.
    vacias = ~(p | o) & LLENO
    cerca = ((vacias << 1) & SIN_A) | ((vacias >> 1) & SIN_H) | (vacias << 8) | (vacias >> 8)
    cerca |= ((vacias << 9) & SIN_A) | ((vacias << 7) & SIN_H)
    cerca |= ((vacias >> 7) & SIN_A) | ((vacias >> 9) & SIN_H)
    valor -= 30 * cuenta(cerca) // ((p | o) & cerca).bit_count() if (p | o) & cerca else 0
    if (p | o).bit_count() > 50:  # al final de la partida cuentan las fichas
        valor += 4 * (p.bit_count() - o.bit_count())
    return valor


class _SinTiempo(Exception):
    pass


class NamiNavegante(Player):
    def __init__(self, tiempo: float = TIEMPO) -> None:
        self.tiempo = tiempo
        self.limite = 0.0
        self.nodos = 0

    @classmethod
    def get_name(cls) -> str:
        return "Nami navegante"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Daniela González", "Marcos González"]

    @classmethod
    def get_description(cls) -> str:
        return ("Alfa-beta con profundización iterativa y tablero en bits: busca esquinas y "
                "movilidad, evita las casillas X/C y calcula el final exacto.")

    @classmethod
    def get_icon(cls) -> str:
        return "🍊"

    def choose_move(self, state: GameState) -> Move:
        legales = legal_moves(state)
        if len(legales) == 1:
            return legales[0]
        p = o = 0
        for f, fila in enumerate(state.board):
            for c, v in enumerate(fila):
                if v == state.player:
                    p |= 1 << (f * 8 + c)
                elif v:
                    o |= 1 << (f * 8 + c)
        self.limite = time.perf_counter() + self.tiempo
        orden = [f * 8 + c for f, c in legales]
        mejor = orden[0]
        for prof in range(1, 65 - (p | o).bit_count()):
            try:
                mejor = self._raiz(p, o, prof, orden)
            except _SinTiempo:
                break
            orden.remove(mejor)
            orden.insert(0, mejor)  # la mejor, primero en la siguiente vuelta
        return divmod(mejor, 8)

    def _raiz(self, p: int, o: int, prof: int, orden: list[int]) -> int:
        alfa, mejor = -10**9, orden[0]
        for i in orden:
            f = volteos(p, o, 1 << i)
            v = -self._buscar(o & ~f, p | f | 1 << i, prof - 1, -10**9, -alfa)
            if v > alfa:
                alfa, mejor = v, i
        return mejor

    def _buscar(self, p: int, o: int, prof: int, alfa: int, beta: int) -> int:
        """Negamax con poda alfa-beta."""
        self.nodos += 1
        if not self.nodos % 256 and time.perf_counter() > self.limite:
            raise _SinTiempo
        mis = jugadas(p, o)
        if not mis:
            if not jugadas(o, p):  # fin de partida: ganar es lo primero
                dif = p.bit_count() - o.bit_count()
                return dif + (GANAR if dif > 0 else -GANAR if dif < 0 else 0)
            return -self._buscar(o, p, prof, -beta, -alfa)  # paso de turno
        if prof == 0:
            return evaluar(p, o)
        hijos = []
        while mis:
            m = mis & -mis
            mis ^= m
            f = volteos(p, o, m)
            hijos.append((o & ~f, p | f | m))
        if prof > 2:  # primero las jugadas que dejan al rival con menos opciones
            hijos.sort(key=lambda h: jugadas(*h).bit_count())
        for hp, ho in hijos:
            alfa = max(alfa, -self._buscar(hp, ho, prof - 1, -beta, -alfa))
            if alfa >= beta:
                break
        return alfa
