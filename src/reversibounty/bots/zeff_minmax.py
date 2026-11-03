"""El jugador minimax Zeff: mira varias jugadas hacia delante antes de elegir.

Usa **minimax con poda alfa-beta** (en su forma *negamax*) y **profundización iterativa**: busca
a profundidad 1, luego 2, 3... y se queda con la mejor jugada de la última profundidad que llegó
a terminar antes de agotar su presupuesto de tiempo (0,5 s por jugada; el torneo da 1 s). Así
nunca se pasa del tiempo y, si le sobra, mira más lejos.

Lo que lo hace rápido y fuerte, de más a menos importante:

* **Tablero en bits.** Dentro de la búsqueda, el tablero son dos enteros de 64 bits (las fichas
  de quien mueve y las del rival). Las jugadas legales y los volteos se calculan desplazando esos
  bits en las 8 direcciones, sin recorrer casilla a casilla. El motor del juego sigue siendo la
  referencia: los tests comprueban que los dos calculan exactamente lo mismo.
* **Orden de las jugadas.** Primero la mejor jugada que se encontró antes para esa posición y
  después las casillas buenas (esquinas) antes que las malas. Con buen orden, la poda descarta
  muchas más ramas.
* **Tabla de transposición.** Recuerda lo que ya ha calculado de cada posición, porque a la misma
  posición se llega por caminos distintos y de una profundidad a la siguiente.
* **Final exacto.** La profundidad sigue creciendo hasta que la búsqueda llega al final de la
  partida en todas sus ramas: a partir de ahí el resultado es exacto y juega perfecto.
* **Libro de aperturas.** Las primeras jugadas, que son las más difíciles de calcular, vienen
  precalculadas por el propio Zeff con búsquedas mucho más largas (ver ``zeff_libro.py``).

La evaluación de una posición, desde el punto de vista de quien mueve, suma:

* **Casillas**: esquinas muy buenas, bordes buenos. Las casillas pegadas a una esquina (X y C)
  solo restan **mientras esa esquina está vacía**, porque es entonces cuando se la regalan al rival.
* **Movilidad**: tener más jugadas que el rival. Pesa más al principio de la partida.
* **Frontera**: fichas que tocan casillas vacías. Tener pocas es bueno: le dan jugadas al rival.
* **Fichas**: solo cuentan al final de la partida.
* En una posición terminal solo cuenta el resultado: ganar pesa más que cualquier otra cosa.
"""

from __future__ import annotations

import random
import time
from typing import Any

from ..game import SIZE, GameState, Move, legal_moves
from ..player import Player
from .zeff_libro import LIBRO

#: Segundos que el bot se da a sí mismo por jugada (el torneo permite 1 s por defecto).
DEFAULT_TIME_LIMIT = 0.5

#: Profundidad máxima. No es un límite práctico: quien para la búsqueda es el reloj, o haber
#: resuelto la partida hasta el final.
MAX_DEPTH = 64

#: Valor de una partida ganada o perdida: mayor que cualquier evaluación intermedia.
WIN_VALUE = 100_000

#: Margen de seguridad: la búsqueda se corta un poco antes de agotar el tiempo.
_MARGEN = 0.02

#: Cada cuántas posiciones se mira el reloj (mirarlo en cada una cuesta tiempo).
_CADA = 256

_INF = 10**9
_LLENO = (1 << 64) - 1


# -- El tablero en bits ------------------------------------------------------- #
#
# La casilla (fila, columna) es el bit fila * 8 + columna. Desplazar los bits 1 posición es
# moverse una columna, 8 es una fila, 7 y 9 las diagonales. Al desplazar en horizontal o en
# diagonal, una ficha de la columna h "saltaría" a la columna a de la fila siguiente: las
# máscaras quitan las columnas (o filas) del borde para que eso no pase.

_HORIZONTAL = 0x7E7E7E7E7E7E7E7E  # sin las columnas a y h
_VERTICAL = 0x00FFFFFFFFFFFF00  # sin las filas 1 y 8
_DIAGONAL = 0x007E7E7E7E7E7E00  # sin los bordes
_DIRECCIONES = ((1, _HORIZONTAL), (8, _VERTICAL), (7, _DIAGONAL), (9, _DIAGONAL))

_SIN_A = 0xFEFEFEFEFEFEFEFE  # todas menos la columna a
_SIN_H = 0x7F7F7F7F7F7F7F7F  # todas menos la columna h


def _jugadas(p: int, o: int) -> int:
    """Las jugadas legales de ``p`` contra ``o``, como un entero con un bit por casilla."""
    vacias = ~(p | o) & _LLENO
    jugadas = 0
    for s, mascara in _DIRECCIONES:
        w = o & mascara
        # Hacia un lado: fichas rivales seguidas a partir de una propia...
        t = w & (p << s)
        t |= w & (t << s)
        t |= w & (t << s)
        t |= w & (t << s)
        t |= w & (t << s)
        t |= w & (t << s)
        jugadas |= vacias & (t << s)  # ...y la casilla vacía que las cierra.
        # Hacia el otro.
        t = w & (p >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        jugadas |= vacias & (t >> s)
    return jugadas


def _volteos(p: int, o: int, m: int) -> int:
    """Las fichas de ``o`` que se dan la vuelta si ``p`` juega en el bit ``m``."""
    volteadas = 0
    for s, mascara in _DIRECCIONES:
        w = o & mascara
        f = 0
        x = m << s
        while x & w:
            f |= x
            x <<= s
        if x & p:
            volteadas |= f
        f = 0
        x = m >> s
        while x & w:
            f |= x
            x >>= s
        if x & p:
            volteadas |= f
    return volteadas


def _vecinas(b: int) -> int:
    """Las casillas que tocan alguna casilla de ``b`` (en las 8 direcciones)."""
    return (
        ((b << 1) & _SIN_A) | ((b >> 1) & _SIN_H) | (b << 8) | (b >> 8)
        | ((b << 9) & _SIN_A) | ((b << 7) & _SIN_H) | ((b >> 7) & _SIN_A) | ((b >> 9) & _SIN_H)
    ) & _LLENO


def _bits(state: GameState) -> tuple[int, int]:
    """El estado como ``(fichas de quien mueve, fichas del rival)``."""
    p = o = 0
    for fila in range(SIZE):
        for columna in range(SIZE):
            valor = state.board[fila][columna]
            if valor == state.player:
                p |= 1 << (fila * SIZE + columna)
            elif valor:
                o |= 1 << (fila * SIZE + columna)
    return p, o


def _indices(b: int) -> list[int]:
    """Las casillas (de 0 a 63) que están a 1 en ``b``."""
    indices = []
    while b:
        bajo = b & -b
        indices.append(bajo.bit_length() - 1)
        b ^= bajo
    return indices


# -- La evaluación ------------------------------------------------------------ #


def _mascara(casillas: list[tuple[int, int]]) -> int:
    resultado = 0
    for fila, columna in casillas:
        resultado |= 1 << (fila * SIZE + columna)
    return resultado


def _simetricas(fila: int, columna: int) -> list[tuple[int, int]]:
    """La casilla y sus equivalentes por simetría (las mismas en las cuatro esquinas)."""
    n = SIZE - 1
    return list({(fila, columna), (fila, n - columna), (n - fila, columna), (n - fila, n - columna),
                 (columna, fila), (columna, n - fila), (n - columna, fila), (n - columna, n - fila)})


#: Peso fijo de las casillas, por grupos de casillas equivalentes. Las X y C (pegadas a una
#: esquina) no están aquí: dependen de si su esquina está ocupada (ver :data:`_ESQUINAS`).
_PESOS: tuple[tuple[int, int], ...] = (
    (_mascara(_simetricas(0, 0)), 120),  # esquinas
    (_mascara(_simetricas(0, 2)), 12),   # bordes junto a las C
    (_mascara(_simetricas(0, 3)), 6),    # centro de los bordes
    (_mascara(_simetricas(2, 2)), 2),    # interior
    (_mascara(_simetricas(1, 2) + _simetricas(1, 3)), -3),  # segunda línea
)

#: Cada esquina con su casilla X (en diagonal) y sus dos casillas C (al lado).
_ESQUINAS = tuple(
    (1 << (f * SIZE + c), 1 << (x_f * SIZE + x_c), _mascara(cs))
    for (f, c), (x_f, x_c), cs in (
        ((0, 0), (1, 1), [(0, 1), (1, 0)]),
        ((0, 7), (1, 6), [(0, 6), (1, 7)]),
        ((7, 0), (6, 1), [(7, 1), (6, 0)]),
        ((7, 7), (6, 6), [(7, 6), (6, 7)]),
    )
)
CASTIGO_X = 50
CASTIGO_C = 20

#: Peso de (movilidad, frontera, fichas) según cuántas casillas vacías quedan.
FASES: tuple[tuple[int, tuple[int, int, int]], ...] = (
    (44, (12, 6, 0)),  # apertura: más de 44 vacías
    (20, (8, 4, 0)),   # medio juego
    (-1, (4, 1, 6)),   # final: 20 vacías o menos
)


def _final(p: int, o: int) -> int:
    """Valor exacto de una posición terminal para ``p``: ganar es siempre lo primero."""
    diferencia = p.bit_count() - o.bit_count()
    if diferencia > 0:
        return WIN_VALUE + diferencia
    if diferencia < 0:
        return -WIN_VALUE + diferencia
    return 0


def _evaluar(p: int, o: int, mis_jugadas: int) -> int:
    """Valor heurístico de una posición no terminal, para quien mueve (``p``)."""
    valor = 0
    for mascara, peso in _PESOS:
        valor += peso * ((p & mascara).bit_count() - (o & mascara).bit_count())
    ocupadas = p | o
    for esquina, x, c in _ESQUINAS:
        if not ocupadas & esquina:  # esquina libre: sus vecinas se la regalan al rival
            valor -= CASTIGO_X * ((p & x).bit_count() - (o & x).bit_count())
            valor -= CASTIGO_C * ((p & c).bit_count() - (o & c).bit_count())

    vacias = ~ocupadas & _LLENO
    n_vacias = vacias.bit_count()
    peso_mov, peso_frontera, peso_fichas = FASES[-1][1]
    for umbral, pesos in FASES:
        if n_vacias > umbral:
            peso_mov, peso_frontera, peso_fichas = pesos
            break

    # int(a / b) redondea hacia cero; a // b redondea hacia abajo y haría que la misma posición
    # valiera +2 para un jugador y -3 para el otro.
    mias = mis_jugadas.bit_count()
    suyas = _jugadas(o, p).bit_count()
    if mias + suyas:
        valor += int(peso_mov * 10 * (mias - suyas) / (mias + suyas))
    cerca = _vecinas(vacias)
    frontera_mia = (p & cerca).bit_count()
    frontera_suya = (o & cerca).bit_count()
    if frontera_mia + frontera_suya:
        valor += int(peso_frontera * 10 * (frontera_suya - frontera_mia) / (frontera_mia + frontera_suya))
    valor += peso_fichas * (p.bit_count() - o.bit_count())
    return valor


def evaluate(state: GameState, me: int) -> int:
    """Valora una posición para el jugador ``me``: cuanto más alta, mejor para él.

    Es la misma evaluación que usa la búsqueda, expuesta para los tests y la documentación.
    """
    p, o = _bits(state)
    if state.player != me:
        p, o = o, p
    mias = _jugadas(p, o)
    if not mias and not _jugadas(o, p):
        return _final(p, o)
    return _evaluar(p, o, mias)


#: Orden en que se prueban las jugadas cuando no hay otra pista: esquinas primero, X al final.
_PRIORIDAD = [0] * 64
for _grupo, _peso in _PESOS:
    for _i in _indices(_grupo):
        _PRIORIDAD[_i] = _peso
for _esquina, _x, _c in _ESQUINAS:
    _PRIORIDAD[_x.bit_length() - 1] = -CASTIGO_X
    for _i in _indices(_c):
        _PRIORIDAD[_i] = -CASTIGO_C


# -- El libro de aperturas ---------------------------------------------------- #
#
# Las 8 simetrías del tablero (4 giros y sus espejos) no cambian el juego: una posición y su
# imagen tienen la misma mejor jugada, girada. El libro guarda solo una de cada familia, la
# "canónica", y aquí se traduce la jugada de vuelta a la posición real.


def _simetrias() -> list[list[int]]:
    """Para cada una de las 8 simetrías, adónde va cada casilla (de 0 a 63)."""
    n = SIZE - 1
    cambios = (
        lambda f, c: (f, c), lambda f, c: (c, n - f), lambda f, c: (n - f, n - c),
        lambda f, c: (n - c, f), lambda f, c: (f, n - c), lambda f, c: (n - f, c),
        lambda f, c: (c, f), lambda f, c: (n - c, n - f),
    )
    return [
        [fila * SIZE + columna for fila, columna in (cambio(i // SIZE, i % SIZE) for i in range(64))]
        for cambio in cambios
    ]


_SIMETRIAS = _simetrias()


def _transformar(b: int, mapa: list[int]) -> int:
    resultado = 0
    for i in _indices(b):
        resultado |= 1 << mapa[i]
    return resultado


def canonical(p: int, o: int) -> tuple[tuple[int, int], list[int]]:
    """La forma canónica de una posición ``(p, o)`` y la simetría que lleva a ella."""
    mejor_clave: tuple[int, int] | None = None
    mejor_mapa = _SIMETRIAS[0]
    for mapa in _SIMETRIAS:
        clave = (_transformar(p, mapa), _transformar(o, mapa))
        if mejor_clave is None or clave < mejor_clave:
            mejor_clave, mejor_mapa = clave, mapa
    assert mejor_clave is not None
    return mejor_clave, mejor_mapa


def _jugada_del_libro(p: int, o: int) -> int | None:
    """La casilla (0-63) que recomienda el libro, o ``None`` si la posición no está."""
    clave, mapa = canonical(p, o)
    casilla = LIBRO.get(clave)
    if casilla is None:
        return None
    return mapa.index(casilla)  # deshacer la simetría


# -- El jugador ------------------------------------------------------------------ #

_EXACTO, _INFERIOR, _SUPERIOR = 0, 1, 2


class _SinTiempo(Exception):
    """Se agotó el tiempo a mitad de una búsqueda: se descarta esa profundidad."""


class ZeffMinmaxPlayer(Player):
    """Minimax con poda alfa-beta, profundización iterativa, final exacto y libro de aperturas.

    Args:
        rng: generador para deshacer empates entre jugadas igual de buenas.
        time_limit: segundos que se da por jugada.
        max_depth: profundidad máxima; por defecto, sin tope práctico.
        use_book: si consulta el libro de aperturas.
    """

    def __init__(
        self,
        rng: random.Random | None = None,
        time_limit: float = DEFAULT_TIME_LIMIT,
        max_depth: int = MAX_DEPTH,
        use_book: bool = True,
    ) -> None:
        self._rng = rng if rng is not None else random.Random()
        self._time_limit = time_limit
        self._max_depth = max_depth
        self._use_book = use_book
        self._limite = 0.0
        self._nodos = 0
        self._cortada = False
        self._tabla: dict[tuple[int, int], tuple[int, int, int, int, bool]] = {}
        #: Cómo fue la última decisión: por qué jugó, profundidad, valor, si fue exacta...
        self.last_search: dict[str, Any] = {}

    @classmethod
    def get_name(cls) -> str:
        return "Zeff minimax"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Marcos Felgueroso"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Minimax con poda alfa-beta y profundidad adaptada al tiempo: mira varias "
            "jugadas hacia delante valorando esquinas y movilidad, y resuelve el final exacto."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "👨‍🍳"

    @classmethod
    def create(cls, seed: int) -> ZeffMinmaxPlayer:
        """Con la misma semilla desempata igual, para repetir partidas."""
        return cls(random.Random(seed))

    def choose_move(self, state: GameState) -> Move:
        inicio = time.perf_counter()
        jugadas = legal_moves(state)
        if len(jugadas) == 1:
            self.last_search = {"motivo": "única jugada", "segundos": 0.0}
            return jugadas[0]

        p, o = _bits(state)
        if self._use_book:
            casilla = _jugada_del_libro(p, o)
            if casilla is not None:
                self.last_search = {"motivo": "libro", "segundos": time.perf_counter() - inicio}
                fila, columna = divmod(casilla, SIZE)
                return fila, columna

        self._limite = inicio + self._time_limit - _MARGEN
        self._nodos = 0
        self._tabla = {}
        # Respuesta de seguridad por si ni la profundidad 1 llega a acabar.
        fila, columna = self._rng.choice(jugadas)
        elegidas = [fila * SIZE + columna]
        valor, profundidad, exacto = 0, 0, False
        orden = self._ordenar(_jugadas(p, o), -1)
        for prof in range(1, self._max_depth + 1):
            self._cortada = False
            try:
                v, empatadas = self._raiz(p, o, prof, orden)
            except _SinTiempo:
                break
            valor, profundidad, elegidas = v, prof, empatadas
            exacto = not self._cortada
            # La mejor jugada de esta vuelta se prueba la primera en la siguiente.
            orden = empatadas + [i for i in orden if i not in empatadas]
            if exacto:  # todas las ramas llegaron al final: no hay nada más que mirar
                break

        casilla = self._rng.choice(elegidas)
        self.last_search = {
            "motivo": "búsqueda",
            "profundidad": profundidad,
            "valor": valor,
            "exacto": exacto,
            "nodos": self._nodos,
            "segundos": time.perf_counter() - inicio,
        }
        fila, columna = divmod(casilla, SIZE)
        return fila, columna

    # -- Búsqueda --------------------------------------------------------------- #

    @staticmethod
    def _ordenar(jugadas: int, primera: int) -> list[int]:
        """Las casillas de ``jugadas``: ``primera`` delante y después por prioridad."""
        orden = sorted(_indices(jugadas), key=_PRIORIDAD.__getitem__, reverse=True)
        if primera in orden:
            orden.remove(primera)
            orden.insert(0, primera)
        return orden

    def _raiz(self, p: int, o: int, prof: int, orden: list[int]) -> tuple[int, list[int]]:
        """Valora cada jugada de la raíz y devuelve el mejor valor y las jugadas que lo tienen.

        Cada jugada se busca con la ventana ``(mejor - 1, +inf)``: una que valga lo mismo que la
        mejor devuelve su valor exacto, y una peor devuelve algo por debajo de ``mejor``. Así un
        empate es un empate de verdad. Con la ventana ``(mejor, +inf)``, que es lo habitual, una
        jugada peor podía devolver justo ``mejor`` como cota y colarse como empate.
        """
        mejor = -_INF
        empatadas: list[int] = []
        for casilla in orden:
            m = 1 << casilla
            f = _volteos(p, o, m)
            alfa = mejor - 1 if mejor > -_INF else -_INF
            valor = -self._buscar(o & ~f, p | m | f, prof - 1, -_INF, -alfa)
            if valor > mejor:
                mejor, empatadas = valor, [casilla]
            elif valor == mejor:
                empatadas.append(casilla)
        return mejor, empatadas

    def _buscar(self, p: int, o: int, prof: int, alfa: int, beta: int) -> int:
        """Negamax con poda alfa-beta: el valor de la posición para quien mueve (``p``).

        Negamax es minimax escrito una sola vez: lo que es bueno para un jugador es igual de malo
        para el otro, así que el valor de una posición es el máximo de ``-valor`` de sus hijas.
        """
        self._nodos += 1
        if not self._nodos % _CADA and time.perf_counter() > self._limite:
            raise _SinTiempo

        jugadas = _jugadas(p, o)
        if not jugadas:
            if not _jugadas(o, p):
                return _final(p, o)
            return -self._buscar(o, p, prof, -beta, -alfa)  # pasa: no gasta profundidad
        if prof <= 0:
            self._cortada = True  # aquí se estima en lugar de calcular hasta el final
            return _evaluar(p, o, jugadas)

        clave = (p, o)
        guardada = self._tabla.get(clave)
        primera = -1
        if guardada is not None:
            g_prof, g_valor, g_tipo, primera, g_exacto = guardada
            if (g_exacto or g_prof >= prof) and (
                g_tipo == _EXACTO
                or (g_tipo == _INFERIOR and g_valor >= beta)
                or (g_tipo == _SUPERIOR and g_valor <= alfa)
            ):
                if not g_exacto:
                    self._cortada = True  # el dato guardado venía de una estimación
                return g_valor

        cortada_antes = self._cortada
        self._cortada = False
        alfa_inicial = alfa
        mejor, mejor_casilla = -_INF, -1
        for casilla in self._ordenar(jugadas, primera):
            m = 1 << casilla
            f = _volteos(p, o, m)
            valor = -self._buscar(o & ~f, p | m | f, prof - 1, -beta, -alfa)
            if valor > mejor:
                mejor, mejor_casilla = valor, casilla
                if valor > alfa:
                    alfa = valor
                    if alfa >= beta:
                        break

        exacto = not self._cortada
        self._cortada = cortada_antes or self._cortada
        if mejor >= beta:
            tipo = _INFERIOR
        elif mejor <= alfa_inicial:
            tipo = _SUPERIOR
        else:
            tipo = _EXACTO
        self._tabla[clave] = (prof, mejor, tipo, mejor_casilla, exacto)
        return mejor
