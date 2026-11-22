"""Car_lu: alfa-beta con ventana nula, tabla de transposición y final exacto con tiempo repartido.

Autoras: Carmen Cuerva y Lucía Argüello.

Cómo decide, en pocas líneas:

* **Tablero en bits.** Dos enteros de 64 bits (mis fichas y las del rival). Las jugadas y los
  volteos se calculan desplazando bits en las 8 direcciones.
* **Búsqueda.** Negamax con poda alfa-beta y *ventana nula* (PVS), con profundidad creciente
  hasta gastar su presupuesto de tiempo. En la raíz también poda: busca la mejor jugada, no
  todas las que empatan con ella, y así llega más hondo con el mismo tiempo.
* **Orden de las jugadas.** Primero la que fue mejor en la búsqueda anterior (tabla de
  transposición); después, cerca de la raíz, las que dejan al rival con menos respuestas, y
  más abajo, las casillas por su valor (esquinas primero, casillas X al final).
* **Evaluación según la fase.** Esquinas, casillas X y C (solo malas con la esquina vacía),
  movilidad, movilidad potencial, frontera, fichas estables de los bordes, una tabla de
  casillas y, al final, la paridad de las vacías. Los pesos (``W``) se ajustaron jugando
  cientos de partidas contra los demás bots del proyecto.
* **Final exacto, con el tiempo repartido.** Con 12 vacías o menos resuelve la partida hasta
  el final. Con 20 o menos, primero busca con la evaluación (40 % del tiempo) y después
  intenta resolverla con lo que queda: si lo consigue y no pierde, juega la jugada exacta; si
  no, la de la evaluación, así que nunca se queda sin jugada. Primero averigua si gana, empata
  o pierde (mucho más rápido que contar fichas) y, si gana, intenta ganar por más fichas, que
  es el primer desempate del torneo. El final también tiene su tabla de transposición.

Solo usa la biblioteca estándar y ``reversibounty``. No usa azar: con la misma posición juega
siempre igual.
"""

from __future__ import annotations

import time

from reversibounty import GameState, Move, Player, legal_moves

#: Segundos que se da por jugada (el torneo permite 1 s; se deja margen).
PRESUPUESTO = 0.6
#: Con estas vacías o menos, primero busca con evaluación y luego intenta resolver el final.
VACIAS_WLD = 20
#: Con estas vacías o menos resuelve el final directamente.
VACIAS_SEGURO = 12
#: Parte del presupuesto para la búsqueda con evaluación cuando después intentará resolver.
FRACCION_ID = 0.4
#: Cada cuántos nodos mira el reloj.
_CADA = 128

_LLENO = (1 << 64) - 1
_SIN_A = 0xFEFEFEFEFEFEFEFE  # sin la columna 0
_SIN_H = 0x7F7F7F7F7F7F7F7F  # sin la columna 7
_INF = 1 << 30
_FINAL = 1 << 20  # un final exacto vale _FINAL + diferencia de fichas

# (desplazamiento, máscara de las fichas rivales que se pueden atravesar sin saltar de borde)
_DIRS = (
    (1, 0x7E7E7E7E7E7E7E7E),
    (8, _LLENO),
    (7, 0x7E7E7E7E7E7E7E7E),
    (9, 0x7E7E7E7E7E7E7E7E),
)


class _SinTiempo(Exception):
    """Se acabó el presupuesto de la jugada."""


# -- Tablero en bits ------------------------------------------------------------ #


def _jugadas(p: int, o: int) -> int:
    """Máscara de las jugadas legales de ``p`` contra ``o``."""
    vacias = ~(p | o) & _LLENO
    res = 0
    for s, mascara in _DIRS:
        w = o & mascara
        t = w & (p << s)
        t |= w & (t << s)
        t |= w & (t << s)
        t |= w & (t << s)
        t |= w & (t << s)
        t |= w & (t << s)
        res |= (t << s) & vacias
        t = w & (p >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        res |= (t >> s) & vacias
    return res


def _volteos(p: int, o: int, m: int) -> int:
    """Fichas de ``o`` que voltea ``p`` al jugar en el bit ``m``."""
    res = 0
    for s, mascara in _DIRS:
        w = o & mascara
        f = 0
        x = (m << s) & _LLENO
        while x & w:
            f |= x
            x = (x << s) & _LLENO
        if x & p:
            res |= f
        f = 0
        x = m >> s
        while x & w:
            f |= x
            x >>= s
        if x & p:
            res |= f
    return res


def _vecinas(b: int) -> int:
    """Casillas adyacentes (en las 8 direcciones) a alguna ficha de ``b``."""
    return (
        ((b << 1) & _SIN_A)
        | ((b >> 1) & _SIN_H)
        | (b << 8)
        | (b >> 8)
        | ((b << 9) & _SIN_A)
        | ((b << 7) & _SIN_H)
        | ((b >> 7) & _SIN_A)
        | ((b >> 9) & _SIN_H)
    ) & _LLENO


def _bits(b: int) -> list[int]:
    res = []
    while b:
        bajo = b & -b
        res.append(bajo.bit_length() - 1)
        b ^= bajo
    return res


def _a_bits(state: GameState) -> tuple[int, int]:
    p = o = 0
    for i in range(64):
        v = state.board[i >> 3][i & 7]
        if v == state.player:
            p |= 1 << i
        elif v:
            o |= 1 << i
    return p, o


# -- Evaluación ----------------------------------------------------------------- #

# Valor de cada casilla (simétrico): esquinas, bordes buenos, centro y casillas peligrosas.
_TABLA = (
    (20, -3, 11, 8),
    (-3, -7, -4, 1),
    (11, -4, 2, 2),
    (8, 1, 2, -3),
)
_VALOR = [_TABLA[min(f, 7 - f)][min(c, 7 - c)] for f in range(8) for c in range(8)]

# Máscaras por valor de casilla, para evaluar la tabla con bit_count en vez de casilla a casilla.
_POR_VALOR: dict[int, int] = {}
for _i, _v in enumerate(_VALOR):
    _POR_VALOR[_v] = _POR_VALOR.get(_v, 0) | (1 << _i)
_MASCARAS_TABLA = tuple((m, v) for v, m in _POR_VALOR.items() if v)

# Cada esquina con su casilla X, sus casillas C y los dos bordes que salen de ella.
_RINCONES = []
for _f, _c in ((0, 0), (0, 7), (7, 0), (7, 7)):
    _df = 1 if _f == 0 else -1
    _dc = 1 if _c == 0 else -1
    _esq = 1 << (_f * 8 + _c)
    _x = 1 << ((_f + _df) * 8 + _c + _dc)
    _cs = (1 << (_f * 8 + _c + _dc)) | (1 << ((_f + _df) * 8 + _c))
    _bh = tuple(1 << (_f * 8 + _c + _dc * k) for k in range(1, 7))
    _bv = tuple(1 << ((_f + _df * k) * 8 + _c) for k in range(1, 7))
    _RINCONES.append((_esq, _x, _cs, _bh, _bv))
_ESQUINAS = 0x8100000000000081
_BORDES = (0xFF, 0xFF << 56, 0x0101010101010101, 0x8080808080808080)


def _estables(b: int, ocupadas: int) -> int:
    """Fichas de ``b`` que ya no se pueden voltear: tiras de borde ancladas en una esquina y
    bordes completos."""
    res = 0
    for esquina, _x, _cs, bh, bv in _RINCONES:
        if b & esquina:
            res |= esquina
            for borde in (bh, bv):
                for bit in borde:
                    if not b & bit:
                        break
                    res |= bit
    for borde in _BORDES:
        if ocupadas & borde == borde:
            res |= b & borde
    return res.bit_count()


#: Pesos de la evaluación. Las tuplas van por fase: apertura (más de 40 vacías), medio juego
#: y final (16 vacías o menos). Ajustados jugando cientos de partidas contra los demás bots.
W = {
    "tabla": 0.5,  # tabla de casillas
    "esq": 150,  # cada esquina
    "x": 60,  # casilla X con su esquina vacía (penaliza)
    "c": 15,  # casilla C con su esquina vacía (penaliza)
    "mov": (14, 10, 5),  # movilidad: cuántas jugadas tengo frente a las del rival
    "pot": (6, 5, 2),  # movilidad potencial: vacías junto a fichas rivales
    "fron": (10, 8, 2),  # frontera: tener pocas fichas junto a vacías
    "est": (6, 10, 14),  # cada ficha estable
    "fich": (0, 0, 2),  # cada ficha (solo al final)
    "pasa": 25,  # el rival tiene que pasar
    "par": 5,  # paridad de las vacías
}


def _evaluar(p: int, o: int, mias: int) -> int:
    """Valor de la posición para quien mueve (``p``); ``mias`` son sus jugadas. Positivo: va
    mejor."""
    ocupadas = p | o
    vacias = ~ocupadas & _LLENO
    n = vacias.bit_count()
    fase = 0 if n > 40 else (1 if n > 16 else 2)
    valor = 0
    for mascara, peso in _MASCARAS_TABLA:
        valor += peso * ((p & mascara).bit_count() - (o & mascara).bit_count())
    valor = int(valor * W["tabla"])
    valor += W["esq"] * ((p & _ESQUINAS).bit_count() - (o & _ESQUINAS).bit_count())
    for esquina, x, cs, _bh, _bv in _RINCONES:
        if not ocupadas & esquina:
            valor -= W["x"] * ((p & x).bit_count() - (o & x).bit_count())
            valor -= W["c"] * ((p & cs).bit_count() - (o & cs).bit_count())
    mm = mias.bit_count()
    mo = _jugadas(o, p).bit_count()
    pm = (vacias & _vecinas(o)).bit_count()
    po = (vacias & _vecinas(p)).bit_count()
    cerca = _vecinas(vacias)
    fm, fo = (p & cerca).bit_count(), (o & cerca).bit_count()
    valor += W["mov"][fase] * 10 * (mm - mo) // (mm + mo + 2)
    valor += W["pot"][fase] * 10 * (pm - po) // (pm + po + 2)
    valor += W["fron"][fase] * 10 * (fo - fm) // (fm + fo + 2)
    if mo == 0:
        valor += W["pasa"]
    valor += W["est"][fase] * (_estables(p, ocupadas) - _estables(o, ocupadas))
    valor += W["fich"][fase] * (p.bit_count() - o.bit_count())
    if n <= 20:
        valor += W["par"] if n & 1 else -W["par"]
    return valor


def _resultado(p: int, o: int) -> int:
    d = p.bit_count() - o.bit_count()
    if d > 0:
        return _FINAL + d
    if d < 0:
        return -_FINAL + d
    return 0


# Orden fijo de casillas, de mejor a peor, para los nodos lejos de la raíz.
_ORDEN_FIJO = sorted(range(64), key=lambda i: -_VALOR[i])


# -- El jugador ------------------------------------------------------------------ #


class CarLu(Player):
    """Negamax alfa-beta con ventana nula, profundidad creciente y final exacto."""

    def __init__(self, presupuesto: float = PRESUPUESTO) -> None:
        self._presupuesto = presupuesto
        self._tabla: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        self._tfin: dict[tuple[int, int], tuple[int, int, int]] = {}
        self._limite = 0.0
        self._nodos = 0

    @classmethod
    def get_name(cls) -> str:
        return "Car_lu"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Carmen Cuerva", "Lucía Argüello"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Alfa-beta con ventana nula y profundidad creciente que poda también en la raíz; "
            "evalúa esquinas, movilidad y fichas estables, y resuelve el final antes de tiempo."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🏴‍☠️"

    @classmethod
    def create(cls, seed: int) -> CarLu:
        return cls()

    # -- Decisión ---------------------------------------------------------------- #

    def choose_move(self, state: GameState) -> Move:
        inicio = time.perf_counter()
        legales = legal_moves(state)
        if len(legales) == 1:
            return legales[0]
        p, o = _a_bits(state)
        self._nodos = 0
        if len(self._tabla) > 300_000:
            self._tabla = {}
        if len(self._tfin) > 300_000:
            self._tfin = {}
        vacias = 64 - (p | o).bit_count()
        orden = self._ordenar_raiz(p, o)
        fin = inicio + self._presupuesto

        if vacias <= VACIAS_SEGURO:
            # Final corto: se resuelve seguro dentro del tiempo.
            self._limite = fin
            mejor = self._resolver(p, o, orden)
            if mejor is not None:
                return divmod(mejor, 8)

        # Profundidad creciente; en el final deja tiempo para intentar resolverlo.
        intentar = vacias <= VACIAS_WLD
        self._limite = inicio + self._presupuesto * (FRACCION_ID if intentar else 1.0)
        mejor = orden[0]
        exacto = False
        for prof in range(1, vacias + 1):
            try:
                valor, casilla = self._raiz(p, o, prof, orden)
            except _SinTiempo:
                break
            mejor = casilla
            orden = [casilla] + [i for i in orden if i != casilla]
            if abs(valor) >= _FINAL or prof >= vacias:
                exacto = True
                break

        if intentar and not exacto:
            self._limite = fin
            resuelta = self._resolver(p, o, orden)
            if resuelta is not None:
                mejor = resuelta
        return divmod(mejor, 8)

    def _resolver(self, p: int, o: int, orden: list[int]) -> int | None:
        """Resolver el final: la jugada si gana o empata (o si pierde con todo), si no ``None``.

        Primero averigua si gana, empata o pierde (ventana -1, 1); si gana, intenta ganar por
        más fichas con el tiempo que quede. Si se acaba el tiempo, devuelve lo que ya sepa.
        """
        try:
            valor, casilla = self._raiz_final(p, o, orden, -1, 1)
        except _SinTiempo:
            return None
        if valor < 0:
            return None  # pierde con juego perfecto: mejor la jugada de la evaluación
        if valor > 0:
            try:
                orden = [casilla] + [i for i in orden if i != casilla]
                _, casilla = self._raiz_final(p, o, orden, 0, _INF)
            except _SinTiempo:
                pass  # ya sabe que gana con ``casilla``: le basta
        return casilla

    # -- Raíz -------------------------------------------------------------------- #

    def _ordenar_raiz(self, p: int, o: int) -> list[int]:
        puntos = []
        for i in _bits(_jugadas(p, o)):
            m = 1 << i
            f = _volteos(p, o, m)
            resp = _jugadas(o & ~f, p | m | f).bit_count()
            puntos.append((_VALOR[i] - 6 * resp, i))
        puntos.sort(reverse=True)
        return [i for _, i in puntos]

    def _raiz(self, p: int, o: int, prof: int, orden: list[int]) -> tuple[int, int]:
        alfa, beta = -_INF, _INF
        mejor = orden[0]
        for k, casilla in enumerate(orden):
            m = 1 << casilla
            f = _volteos(p, o, m)
            np, no = o & ~f, p | m | f
            if k == 0:
                v = -self._buscar(np, no, prof - 1, -beta, -alfa)
            else:
                v = -self._buscar(np, no, prof - 1, -alfa - 1, -alfa)
                if v > alfa:
                    v = -self._buscar(np, no, prof - 1, -beta, -alfa)
            if v > alfa:
                alfa, mejor = v, casilla
        return alfa, mejor

    def _raiz_final(
        self, p: int, o: int, orden: list[int], alfa: int, beta: int
    ) -> tuple[int, int]:
        mejor = orden[0]
        valor = -_INF
        for casilla in orden:
            m = 1 << casilla
            f = _volteos(p, o, m)
            v = -self._final(o & ~f, p | m | f, -beta, -max(alfa, valor), False)
            if v > valor:
                valor, mejor = v, casilla
                if valor >= beta:
                    break
        return valor, mejor

    # -- Búsqueda con evaluación --------------------------------------------------- #

    def _reloj(self) -> None:
        self._nodos += 1
        if not self._nodos % _CADA and time.perf_counter() > self._limite:
            raise _SinTiempo

    def _buscar(self, p: int, o: int, prof: int, alfa: int, beta: int) -> int:
        self._reloj()
        jugadas = _jugadas(p, o)
        if not jugadas:
            if not _jugadas(o, p):
                return _resultado(p, o)
            return -self._buscar(o, p, prof, -beta, -alfa)
        if prof <= 0:
            return _evaluar(p, o, jugadas)

        clave = (p, o)
        guardado = self._tabla.get(clave)
        primera = -1
        if guardado is not None:
            g_prof, g_tipo, g_valor, primera = guardado
            if g_prof >= prof:
                if g_tipo == 0:
                    return g_valor
                if g_tipo == 1 and g_valor >= beta:
                    return g_valor
                if g_tipo == -1 and g_valor <= alfa:
                    return g_valor

        if prof >= 3:
            puntos = []
            for i in _bits(jugadas):
                m = 1 << i
                f = _volteos(p, o, m)
                puntos.append((_VALOR[i] - 6 * _jugadas(o & ~f, p | m | f).bit_count(), i))
            puntos.sort(reverse=True)
            orden = [i for _, i in puntos]
        else:
            orden = [i for i in _ORDEN_FIJO if jugadas >> i & 1]
        if primera >= 0 and jugadas >> primera & 1:
            orden.remove(primera)
            orden.insert(0, primera)

        alfa0 = alfa
        mejor_v, mejor_i = -_INF, orden[0]
        for k, i in enumerate(orden):
            m = 1 << i
            f = _volteos(p, o, m)
            np, no = o & ~f, p | m | f
            if k == 0:
                v = -self._buscar(np, no, prof - 1, -beta, -alfa)
            else:
                v = -self._buscar(np, no, prof - 1, -alfa - 1, -alfa)
                if alfa < v < beta:
                    v = -self._buscar(np, no, prof - 1, -beta, -alfa)
            if v > mejor_v:
                mejor_v, mejor_i = v, i
                if v > alfa:
                    alfa = v
                    if alfa >= beta:
                        break

        tipo = 1 if mejor_v >= beta else (-1 if mejor_v <= alfa0 else 0)
        self._tabla[clave] = (prof, tipo, mejor_v, mejor_i)
        return mejor_v

    # -- Final exacto --------------------------------------------------------------- #

    def _final(self, p: int, o: int, alfa: int, beta: int, paso: bool) -> int:
        self._reloj()
        jugadas = _jugadas(p, o)
        if not jugadas:
            if paso:
                return _resultado(p, o)
            return -self._final(o, p, -beta, -alfa, True)
        vacias = ~(p | o) & _LLENO
        n = vacias.bit_count()
        clave = (p, o)
        primera = -1
        if n > 6:
            guardado = self._tfin.get(clave)
            if guardado is not None:
                g_tipo, g_valor, primera = guardado
                if g_tipo == 0:
                    return g_valor
                if g_tipo == 1 and g_valor >= beta:
                    return g_valor
                if g_tipo == -1 and g_valor <= alfa:
                    return g_valor
            puntos = []
            for i in _bits(jugadas):
                m = 1 << i
                f = _volteos(p, o, m)
                puntos.append((_jugadas(o & ~f, p | m | f).bit_count() * 16 - _VALOR[i], i))
            puntos.sort()
            orden = [i for _, i in puntos]
            if primera >= 0 and jugadas >> primera & 1:
                orden.remove(primera)
                orden.insert(0, primera)
        else:
            orden = [i for i in _ORDEN_FIJO if jugadas >> i & 1]
        alfa0 = alfa
        mejor, mejor_i = -_INF, orden[0]
        for i in orden:
            m = 1 << i
            f = _volteos(p, o, m)
            v = -self._final(o & ~f, p | m | f, -beta, -alfa, False)
            if v > mejor:
                mejor, mejor_i = v, i
                if v > alfa:
                    alfa = v
                    if alfa >= beta:
                        break
        if n > 6:
            tipo = 1 if mejor >= beta else (-1 if mejor <= alfa0 else 0)
            self._tfin[clave] = (tipo, mejor, mejor_i)
        return mejor
