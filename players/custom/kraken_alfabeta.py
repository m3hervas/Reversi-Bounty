"""Kraken alfa-beta: minimax con poda alfa-beta, profundización iterativa y final exacto.

Cómo decide, en pocas líneas:

* **Busca hacia delante** con negamax y poda alfa-beta (con ventana nula, PVS), a profundidad
  1, 2, 3... hasta agotar su presupuesto de tiempo (0,6 s por jugada; el torneo da 1 s).
* **Tablero en bits**: dos enteros de 64 bits (fichas propias y rivales) para calcular jugadas
  y volteos muy rápido, y una tabla de transposición que se conserva entre jugadas.
* **Orden "lo más rápido primero"**: prueba antes las jugadas que dejan al rival con menos
  respuestas, porque así la poda descarta más ramas.
* **Evaluación combinada** que cambia según la fase: esquinas y bordes, casillas X y C (solo
  malas si su esquina está libre), movilidad, movilidad potencial, frontera, fichas estables
  ancladas a las esquinas y, al final, paridad y número de fichas.
* **Final exacto**: con 14 casillas vacías o menos intenta resolver la partida hasta el final
  (primero si gana, empata o pierde; después por cuántas fichas).

Solo usa la biblioteca estándar y ``reversibounty``. Con la misma semilla desempata igual.
"""

from __future__ import annotations

import random
import time

from reversibounty import GameState, Move, Player, legal_moves

#: Segundos que se da por jugada (el torneo permite 1 s).
PRESUPUESTO = 0.6
#: Vacías a partir de las que intenta resolver el final de forma exacta.
VACIAS_FINAL = 14
#: Cada cuántos nodos mira el reloj.
_CADA = 256

_LLENO = (1 << 64) - 1
_INF = 10**9
_GANA = 100_000
_DIRS = (
    (1, 0x7E7E7E7E7E7E7E7E),
    (8, 0x00FFFFFFFFFFFF00),
    (7, 0x007E7E7E7E7E7E00),
    (9, 0x007E7E7E7E7E7E00),
)
_SIN_A = 0xFEFEFEFEFEFEFEFE
_SIN_H = 0x7F7F7F7F7F7F7F7F


class _SinTiempo(Exception):
    pass


# -- Tablero en bits ------------------------------------------------------------ #


def _jugadas(p: int, o: int) -> int:
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
        res |= vacias & (t << s)
        t = w & (p >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        t |= w & (t >> s)
        res |= vacias & (t >> s)
    return res


def _volteos(p: int, o: int, m: int) -> int:
    res = 0
    for s, mascara in _DIRS:
        w = o & mascara
        f = 0
        x = m << s
        while x & w:
            f |= x
            x <<= s
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
    return (
        ((b << 1) & _SIN_A) | ((b >> 1) & _SIN_H) | (b << 8) | (b >> 8)
        | ((b << 9) & _SIN_A) | ((b << 7) & _SIN_H) | ((b >> 7) & _SIN_A) | ((b >> 9) & _SIN_H)
    ) & _LLENO


def _indices(b: int) -> list[int]:
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


def _casilla(i: int) -> str:
    return "abcdefgh"[i & 7] + str((i >> 3) + 1)


# -- Evaluación ----------------------------------------------------------------- #


def _mascara(casillas: list[tuple[int, int]]) -> int:
    res = 0
    for f, c in casillas:
        res |= 1 << (f * 8 + c)
    return res


def _sim(f: int, c: int) -> list[tuple[int, int]]:
    return list({(f, c), (f, 7 - c), (7 - f, c), (7 - f, 7 - c),
                 (c, f), (c, 7 - f), (7 - c, f), (7 - c, 7 - f)})


_ESQ = _mascara(_sim(0, 0))
_PESOS = (
    (_ESQ, 100),
    (_mascara(_sim(0, 2)), 10),
    (_mascara(_sim(0, 3)), 5),
    (_mascara(_sim(2, 2)), 2),
    (_mascara(_sim(1, 2) + _sim(1, 3)), -2),
)
# (esquina, casilla X, casillas C, los dos bordes que salen de la esquina como listas de bits)
_RINCONES = []
for (_f, _c), (_xf, _xc), _cs, _df, _dc in (
    ((0, 0), (1, 1), [(0, 1), (1, 0)], 1, 1),
    ((0, 7), (1, 6), [(0, 6), (1, 7)], 1, -1),
    ((7, 0), (6, 1), [(7, 1), (6, 0)], -1, 1),
    ((7, 7), (6, 6), [(7, 6), (6, 7)], -1, -1),
):
    _borde_h = [1 << (_f * 8 + _c + _dc * k) for k in range(1, 7)]
    _borde_v = [1 << ((_f + _df * k) * 8 + _c) for k in range(1, 7)]
    _RINCONES.append((1 << (_f * 8 + _c), 1 << (_xf * 8 + _xc), _mascara(_cs), _borde_h, _borde_v))


def _estables(b: int) -> int:
    """Fichas de ``b`` que ya no se pueden voltear: esquinas y bordes pegados a ellas."""
    res = 0
    for esquina, _x, _c, borde_h, borde_v in _RINCONES:
        if b & esquina:
            res |= esquina
            for borde in (borde_h, borde_v):
                for bit in borde:
                    if not b & bit:
                        break
                    res |= bit
    return res.bit_count()


def _evaluar(p: int, o: int, mias: int) -> int:
    valor = 0
    for mascara, peso in _PESOS:
        valor += peso * ((p & mascara).bit_count() - (o & mascara).bit_count())
    ocupadas = p | o
    for esquina, x, c, _bh, _bv in _RINCONES:
        if not ocupadas & esquina:
            valor -= 40 * ((p & x).bit_count() - (o & x).bit_count())
            valor -= 15 * ((p & c).bit_count() - (o & c).bit_count())
    vacias = ~ocupadas & _LLENO
    n = vacias.bit_count()
    if n > 44:
        k_mov, k_pot, k_fron, k_est, k_fich = 14, 6, 6, 8, 0
    elif n > 18:
        k_mov, k_pot, k_fron, k_est, k_fich = 10, 5, 5, 12, 0
    else:
        k_mov, k_pot, k_fron, k_est, k_fich = 5, 2, 2, 15, 3
    nm = mias.bit_count()
    ns = _jugadas(o, p).bit_count()
    valor += k_mov * 10 * (nm - ns) // (nm + ns + 2)
    pot_m = (vacias & _vecinas(o)).bit_count()
    pot_s = (vacias & _vecinas(p)).bit_count()
    valor += k_pot * 10 * (pot_m - pot_s) // (pot_m + pot_s + 2)
    cerca = _vecinas(vacias)
    fm = (p & cerca).bit_count()
    fs = (o & cerca).bit_count()
    valor += k_fron * 10 * (fs - fm) // (fm + fs + 2)
    valor += k_est * (_estables(p) - _estables(o))
    valor += k_fich * (p.bit_count() - o.bit_count())
    if n <= 18:
        valor += 6 if n % 2 else -6  # paridad: quien juega con vacías impares suele cerrar
    return valor


def _final(p: int, o: int) -> int:
    d = p.bit_count() - o.bit_count()
    return _GANA + d if d > 0 else (-_GANA + d if d < 0 else 0)


_PRIORIDAD = [0] * 64
for _m, _peso in _PESOS:
    for _i in _indices(_m):
        _PRIORIDAD[_i] = _peso
for _e, _x, _c, _bh, _bv in _RINCONES:
    _PRIORIDAD[_x.bit_length() - 1] = -40
    for _i in _indices(_c):
        _PRIORIDAD[_i] = -15


# -- El jugador ------------------------------------------------------------------ #


class KrakenAlfaBeta(Player):
    """Negamax alfa-beta con profundización iterativa, PVS y final exacto."""

    def __init__(self, rng: random.Random | None = None, presupuesto: float = PRESUPUESTO) -> None:
        self._rng = rng if rng is not None else random.Random()
        self._presupuesto = presupuesto
        self._tabla: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        self._limite = 0.0
        self._nodos = 0
        #: Por qué eligió la última jugada, en una frase (para mostrar partidas).
        self.razon = ""

    @classmethod
    def get_name(cls) -> str:
        return "Kraken alfa-beta"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Antonio Orteu", "María Sanz", "Álvaro Domingo"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Minimax alfa-beta con profundidad creciente, orden 'lo más rápido primero' y "
            "evaluación de esquinas, movilidad, frontera y fichas estables; resuelve el final exacto."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🐙"

    @classmethod
    def create(cls, seed: int) -> KrakenAlfaBeta:
        return cls(random.Random(seed))

    def choose_move(self, state: GameState) -> Move:
        inicio = time.perf_counter()
        legales = legal_moves(state)
        if len(legales) == 1:
            self.razon = "Es la única jugada legal."
            return legales[0]
        p, o = _a_bits(state)
        self._limite = inicio + self._presupuesto
        self._nodos = 0
        if len(self._tabla) > 400_000:
            self._tabla = {}
        vacias = 64 - (p | o).bit_count()
        orden = self._ordenar(p, o, _jugadas(p, o), -1, True)
        f, c = legales[self._rng.randrange(len(legales))]
        mejor = [f * 8 + c]
        valor, prof_ok = 0, 0

        if vacias <= VACIAS_FINAL:
            try:
                v, casilla = self._resolver_raiz(p, o, orden, -1, 1)
                if v > 0:
                    try:
                        v, casilla = self._resolver_raiz(p, o, [casilla] + orden, -_INF, _INF)
                    except _SinTiempo:
                        pass  # ya sabe que gana con esa jugada: le basta
                resultado = "gana" if v > 0 else ("empata" if v == 0 else "pierde")
                self.razon = (
                    f"Final calculado hasta el último movimiento: con {_casilla(casilla)} "
                    f"{resultado} jugando perfecto."
                )
                return divmod(casilla, 8)
            except _SinTiempo:
                pass

        for prof in range(1, vacias + 1):
            try:
                v, elegidas = self._raiz(p, o, prof, orden)
            except _SinTiempo:
                break
            valor, prof_ok, mejor = v, prof, elegidas
            orden = elegidas + [i for i in orden if i not in elegidas]
            if abs(v) >= _GANA:
                break
        casilla = mejor[self._rng.randrange(len(mejor))]
        if abs(valor) >= _GANA:
            texto = "ve una victoria segura" if valor > 0 else "ve que va perdiendo y resiste"
        elif valor > 30:
            texto = "su evaluación dice que va claramente por delante"
        elif valor < -30:
            texto = "elige la jugada que menos empeora su posición"
        else:
            texto = "posición igualada: busca esquinas, movilidad y fichas estables"
        self.razon = f"Mirando {prof_ok} jugadas hacia delante, {_casilla(casilla)}: {texto}."
        return divmod(casilla, 8)

    # -- Ordenación ----------------------------------------------------------------- #

    @staticmethod
    def _ordenar(p: int, o: int, jugadas: int, primera: int, rapido: bool) -> list[int]:
        casillas = _indices(jugadas)
        if rapido:
            puntos = []
            for i in casillas:
                m = 1 << i
                f = _volteos(p, o, m)
                resp = _jugadas(o & ~f, p | m | f).bit_count()
                puntos.append((_PRIORIDAD[i] - 12 * resp, i))
            puntos.sort(reverse=True)
            casillas = [i for _, i in puntos]
        else:
            casillas.sort(key=_PRIORIDAD.__getitem__, reverse=True)
        if primera in casillas:
            casillas.remove(primera)
            casillas.insert(0, primera)
        return casillas

    # -- Búsqueda con evaluación ------------------------------------------------------- #

    def _raiz(self, p: int, o: int, prof: int, orden: list[int]) -> tuple[int, list[int]]:
        mejor = -_INF
        elegidas: list[int] = []
        for casilla in orden:
            m = 1 << casilla
            f = _volteos(p, o, m)
            alfa = mejor - 1 if mejor > -_INF else -_INF
            v = -self._buscar(o & ~f, p | m | f, prof - 1, -_INF, -alfa)
            if v > mejor:
                mejor, elegidas = v, [casilla]
            elif v == mejor:
                elegidas.append(casilla)
        return mejor, elegidas

    def _buscar(self, p: int, o: int, prof: int, alfa: int, beta: int) -> int:
        self._nodos += 1
        if not self._nodos % _CADA and time.perf_counter() > self._limite:
            raise _SinTiempo
        jugadas = _jugadas(p, o)
        if not jugadas:
            if not _jugadas(o, p):
                return _final(p, o)
            return -self._buscar(o, p, prof, -beta, -alfa)
        if prof <= 0:
            return _evaluar(p, o, jugadas)
        clave = (p, o)
        guardada = self._tabla.get(clave)
        primera = -1
        if guardada is not None:
            g_prof, g_val, g_tipo, primera = guardada
            if g_prof >= prof and (
                g_tipo == 0 or (g_tipo == 1 and g_val >= beta) or (g_tipo == 2 and g_val <= alfa)
            ):
                return g_val
        alfa0 = alfa
        mejor, mejor_c = -_INF, -1
        primero = True
        for casilla in self._ordenar(p, o, jugadas, primera, prof >= 3):
            m = 1 << casilla
            f = _volteos(p, o, m)
            np_, no = o & ~f, p | m | f
            if primero:
                v = -self._buscar(np_, no, prof - 1, -beta, -alfa)
                primero = False
            else:
                v = -self._buscar(np_, no, prof - 1, -alfa - 1, -alfa)
                if alfa < v < beta:
                    v = -self._buscar(np_, no, prof - 1, -beta, -v)
            if v > mejor:
                mejor, mejor_c = v, casilla
                if v > alfa:
                    alfa = v
                    if alfa >= beta:
                        break
        tipo = 1 if mejor >= beta else (2 if mejor <= alfa0 else 0)
        self._tabla[clave] = (prof, mejor, tipo, mejor_c)
        return mejor

    # -- Final exacto ---------------------------------------------------------------- #

    def _resolver_raiz(self, p: int, o: int, orden: list[int], alfa: int, beta: int) -> tuple[int, int]:
        mejor, mejor_c = -_INF, orden[0]
        for casilla in orden:
            m = 1 << casilla
            f = _volteos(p, o, m)
            v = -self._resolver(o & ~f, p | m | f, -beta, -max(alfa, mejor))
            if v > mejor:
                mejor, mejor_c = v, casilla
                if mejor >= beta:
                    break
        return mejor, mejor_c

    def _resolver(self, p: int, o: int, alfa: int, beta: int) -> int:
        """Diferencia de fichas final con juego perfecto (dentro de la ventana alfa-beta)."""
        self._nodos += 1
        if not self._nodos % _CADA and time.perf_counter() > self._limite:
            raise _SinTiempo
        jugadas = _jugadas(p, o)
        if not jugadas:
            if not _jugadas(o, p):
                return p.bit_count() - o.bit_count()
            return -self._resolver(o, p, -beta, -alfa)
        vacias = 64 - (p | o).bit_count()
        if vacias > 6:
            casillas = self._ordenar(p, o, jugadas, -1, True)
        else:
            casillas = _indices(jugadas)
        mejor = -_INF
        for casilla in casillas:
            m = 1 << casilla
            f = _volteos(p, o, m)
            v = -self._resolver(o & ~f, p | m | f, -beta, -alfa)
            if v > mejor:
                mejor = v
                if v > alfa:
                    alfa = v
                    if alfa >= beta:
                        break
        return mejor
