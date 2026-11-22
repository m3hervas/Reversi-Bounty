"""Minimax con poda alfa-beta, profundización iterativa y una evaluación por fases.

Dentro de la búsqueda el tablero se guarda en bits: dos números de 64 bits, uno con las fichas
de quien mueve (``yo``) y otro con las del rival (``el``). La casilla ``(fila, columna)`` es el
bit ``fila * 8 + columna``. Así las jugadas legales y los volteos se calculan desplazando los 64
bits a la vez en lugar de recorrer el tablero casilla a casilla.
"""

import random
import time

from reversibounty import GameState, Move, Player

# Tiempo que se da para pensar cada jugada. El torneo concede 1 s; el resto es margen.
TIEMPO_POR_JUGADA = 0.5
PROFUNDIDAD_MAXIMA = 60
VICTORIA = 1_000_000
INFINITO = 2 * VICTORIA  # mayor que cualquier valor posible

# Valor de cada casilla para quien la ocupa. Esquinas muy buenas; las casillas junto a una
# esquina vacía (X y C), malas, porque le regalan la esquina al rival.
PESOS = (
    (100, -20, 10, 5, 5, 10, -20, 100),
    (-20, -50, -2, -2, -2, -2, -50, -20),
    (10, -2, 1, 1, 1, 1, -2, 10),
    (5, -2, 1, 0, 0, 1, -2, 5),
    (5, -2, 1, 0, 0, 1, -2, 5),
    (10, -2, 1, 1, 1, 1, -2, 10),
    (-20, -50, -2, -2, -2, -2, -50, -20),
    (100, -20, 10, 5, 5, 10, -20, 100),
)

# ---------------------------------------------------------------------- tablero en bits

LLENO = 0xFFFFFFFFFFFFFFFF
SIN_COLUMNA_A = 0xFEFEFEFEFEFEFEFE  # todo menos la columna 0
SIN_COLUMNA_H = 0x7F7F7F7F7F7F7F7F  # todo menos la columna 7


def bit(fila: int, columna: int) -> int:
    return 1 << (fila * 8 + columna)


def casilla(b: int) -> Move:
    """Convierte un número con un único bit encendido en ``(fila, columna)``."""
    indice = b.bit_length() - 1
    return indice >> 3, indice & 7


# Desplazar todo el tablero una casilla en cada dirección. La máscara borra lo que se saldría
# por un lado y aparecería por el otro (la columna h no debe saltar a la columna a).
def _este(x: int) -> int:
    return (x << 1) & SIN_COLUMNA_A & LLENO


def _oeste(x: int) -> int:
    return (x >> 1) & SIN_COLUMNA_H


def _sur(x: int) -> int:
    return (x << 8) & LLENO


def _norte(x: int) -> int:
    return x >> 8


def _sureste(x: int) -> int:
    return (x << 9) & SIN_COLUMNA_A & LLENO


def _suroeste(x: int) -> int:
    return (x << 7) & SIN_COLUMNA_H & LLENO


def _noreste(x: int) -> int:
    return (x >> 7) & SIN_COLUMNA_A


def _noroeste(x: int) -> int:
    return (x >> 9) & SIN_COLUMNA_H


DIRECCIONES = (_este, _oeste, _sur, _norte, _sureste, _suroeste, _noreste, _noroeste)


def a_bits(state: GameState) -> tuple[int, int]:
    """Convierte un ``GameState`` en ``(yo, el)``, con ``yo`` el color que mueve."""
    yo = el = 0
    for f, fila in enumerate(state.board):
        for c, valor in enumerate(fila):
            if valor == state.player:
                yo |= bit(f, c)
            elif valor:
                el |= bit(f, c)
    return yo, el


def jugadas(yo: int, el: int) -> int:
    """Todas las jugadas legales de ``yo``, como un número con un bit por jugada."""
    vacias = ~(yo | el) & LLENO
    resultado = 0
    for mover in DIRECCIONES:
        # Fichas del rival pegadas a las mías, y se alarga la fila hasta 6 fichas.
        fila = mover(yo) & el
        fila |= mover(fila) & el
        fila |= mover(fila) & el
        fila |= mover(fila) & el
        fila |= mover(fila) & el
        fila |= mover(fila) & el
        # La jugada es la casilla vacía justo después de la fila.
        resultado |= mover(fila) & vacias
    return resultado


def volteos(yo: int, el: int, jugada: int) -> int:
    """Las fichas del rival que voltea ``jugada`` (un único bit)."""
    resultado = 0
    for mover in DIRECCIONES:
        fila = 0
        x = mover(jugada)
        while x & el:
            fila |= x
            x = mover(x)
        if x & yo:  # la fila acaba en una ficha mía: se voltea
            resultado |= fila
    return resultado


def separar(b: int) -> list[int]:
    """Separa un número en sus bits encendidos."""
    lista = []
    while b:
        menor = b & -b
        lista.append(menor)
        b ^= menor
    return lista


# Los pesos agrupados por valor: para cada peso, un número con todas sus casillas.
MASCARAS_PESO: tuple[tuple[int, int], ...] = tuple(
    (peso, sum(bit(f, c) for f in range(8) for c in range(8) if PESOS[f][c] == peso))
    for peso in sorted({p for fila in PESOS for p in fila} - {0})
)

# Para cada esquina, sus casillas X y C con su peso. Cuando la esquina ya está ocupada, esas
# casillas dejan de ser peligrosas y su peso negativo no cuenta.
VECINAS_DE_ESQUINA: tuple[tuple[int, tuple[tuple[int, int], ...]], ...] = tuple(
    (bit(fe, ce), tuple((bit(f, c), PESOS[f][c]) for f, c in vecinas))
    for (fe, ce), vecinas in (
        ((0, 0), ((0, 1), (1, 0), (1, 1))),
        ((0, 7), ((0, 6), (1, 7), (1, 6))),
        ((7, 0), ((7, 1), (6, 0), (6, 1))),
        ((7, 7), ((7, 6), (6, 7), (6, 6))),
    )
)

# Las mejores casillas se prueban antes: así la poda alfa-beta descarta más.
PRIORIDAD = {bit(f, c): -PESOS[f][c] for f in range(8) for c in range(8)}


# ---------------------------------------------------------------------- evaluación


def evaluar(yo: int, el: int, mis_jugadas: int) -> int:
    """Puntúa una posición no terminal para quien mueve (``yo``).

    ``mis_jugadas`` es el número de jugadas legales de ``yo``, que la búsqueda ya ha calculado.
    """
    # 1. Posición: suma de pesos de mis fichas menos las del rival.
    posicion = 0
    for peso, mascara in MASCARAS_PESO:
        posicion += peso * ((yo & mascara).bit_count() - (el & mascara).bit_count())
    ocupadas = yo | el
    for esquina, vecinas in VECINAS_DE_ESQUINA:
        if ocupadas & esquina:
            for b, peso in vecinas:
                if yo & b:
                    posicion -= peso
                elif el & b:
                    posicion += peso

    # 2. Movilidad: tener más jugadas que el rival.
    sus_jugadas = jugadas(el, yo).bit_count()
    total = mis_jugadas + sus_jugadas
    # int(... / ...) redondea hacia cero, igual para los dos jugadores; ``//`` redondearía hacia
    # abajo y la misma posición valdría distinto vista por cada lado.
    movilidad = int(100 * (mis_jugadas - sus_jugadas) / total) if total else 0

    # 3. Fichas: solo importan al final. Todo va multiplicado por 2 para no dividir la
    # movilidad entre 2 en el final.
    vacias = 64 - ocupadas.bit_count()
    if vacias > 40:  # apertura
        return 2 * posicion + 4 * movilidad
    if vacias > 14:  # medio juego
        return 2 * posicion + 2 * movilidad
    fichas = yo.bit_count() - el.bit_count()
    return 2 * posicion + movilidad + 10 * fichas  # final


def resultado_final(yo: int, el: int) -> int:
    """Valor exacto de una partida terminada, para ``yo``."""
    diferencia = yo.bit_count() - el.bit_count()
    if diferencia > 0:
        return VICTORIA + diferencia
    if diferencia < 0:
        return -VICTORIA + diferencia
    return 0


# ---------------------------------------------------------------------- el jugador


class SinTiempo(Exception):
    """Se lanza dentro de la búsqueda cuando se acaba el tiempo de la jugada."""


class MinimaxZena(Player):
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()
        self._limite = 0.0
        self.ultima_profundidad = 0  # profundidad completa de la última jugada (para medir)

    @classmethod
    def get_name(cls) -> str:
        return "Minimax de Zena"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Zena Saez"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Minimax con poda alfa-beta que piensa cada vez más lejos mientras le dura el tiempo."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🦉"

    @classmethod
    def create(cls, seed: int) -> "MinimaxZena":
        return cls(random.Random(seed))

    # ------------------------------------------------------------------ decisión

    def choose_move(self, state: GameState) -> Move:
        yo, el = a_bits(state)
        candidatas = separar(jugadas(yo, el))
        self.ultima_profundidad = 0
        if len(candidatas) == 1:
            return casilla(candidatas[0])

        self._limite = time.perf_counter() + TIEMPO_POR_JUGADA
        candidatas.sort(key=PRIORIDAD.__getitem__)
        mejor = self._rng.choice(candidatas)

        # Profundización iterativa: 1, 2, 3... Si una profundidad no termina a tiempo se
        # descarta y se juega lo que dijo la última completa.
        for profundidad in range(1, PROFUNDIDAD_MAXIMA + 1):
            try:
                valor, mejores = self._raiz(yo, el, candidatas, profundidad)
            except SinTiempo:
                break
            mejor = self._rng.choice(mejores)
            self.ultima_profundidad = profundidad
            # La mejor jugada se prueba la primera en la siguiente vuelta.
            candidatas.remove(mejor)
            candidatas.insert(0, mejor)
            if abs(valor) >= VICTORIA:  # ya sabe cómo acaba la partida
                break
        return casilla(mejor)

    def _raiz(
        self, yo: int, el: int, candidatas: list[int], profundidad: int
    ) -> tuple[int, list[int]]:
        """Valora cada jugada de la raíz y devuelve el mejor valor y las jugadas que lo logran."""
        mejor_valor = -INFINITO
        mejores: list[int] = []
        for jugada in candidatas:
            v = volteos(yo, el, jugada)
            # Ventana (mejor - 1, inf): una jugada igual de buena da su valor exacto, así los
            # empates son empates de verdad y no cotas de la poda.
            valor = -self._negamax(
                el & ~v, yo | jugada | v, profundidad - 1, -INFINITO, 1 - mejor_valor
            )
            if valor > mejor_valor:
                mejor_valor, mejores = valor, [jugada]
            elif valor == mejor_valor:
                mejores.append(jugada)
        return mejor_valor, mejores

    # ------------------------------------------------------------------ búsqueda

    def _negamax(self, yo: int, el: int, profundidad: int, alfa: int, beta: int) -> int:
        """Minimax en forma negamax: valor de la posición para quien mueve (``yo``)."""
        if time.perf_counter() > self._limite:
            raise SinTiempo

        posibles = jugadas(yo, el)
        if not posibles:
            if not jugadas(el, yo):  # nadie puede mover: partida terminada
                return resultado_final(yo, el)
            # Paso: le toca al rival sin gastar profundidad.
            return -self._negamax(el, yo, profundidad, -beta, -alfa)
        if profundidad == 0:
            return evaluar(yo, el, posibles.bit_count())

        lista = separar(posibles)
        lista.sort(key=PRIORIDAD.__getitem__)
        mejor = -INFINITO
        for jugada in lista:
            v = volteos(yo, el, jugada)
            valor = -self._negamax(el & ~v, yo | jugada | v, profundidad - 1, -beta, -alfa)
            if valor > mejor:
                mejor = valor
                if valor > alfa:
                    alfa = valor
                    if alfa >= beta:
                        break  # poda: el rival nunca dejará llegar aquí
        return mejor
