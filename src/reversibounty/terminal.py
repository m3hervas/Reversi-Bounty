"""Partida completa de Reversi en la terminal, para dos personas y un teclado.

Se instala con el paquete y ofrece dos comandos::

    reversi-play          # solo texto, sirve en cualquier terminal
    reversi-play-color    # tablero con colores y fichas grandes

Este módulo NO imprime ni lee nada al importarse: solo lo hacen las funciones
``main_texto`` y ``main_color`` cuando se ejecuta uno de los comandos. Así la librería
sigue siendo importable y silenciosa, y el bucle usa solo la API pública del motor
(``initial_state``, ``legal_moves``, ``apply_move``...). Eso sirve de prueba de que
esa API es cómoda: no hace falta tocar el interior de ``GameState``, ni llevar fuera
una variable de turno, ni tratar el primer turno como un caso especial.

La lógica de pantalla y teclado se separa en funciones que reciben "cómo leer" y
"cómo escribir", de modo que los tests pueden jugar una partida entera sin teclado.

Dos modos de dibujo:

* Con color: casillas de dos líneas con fichas grandes que parecen redondas, tablero
  de dos verdes alternados y la última jugada resaltada en dorado.
* Sin color: solo ASCII (``X`` negras, ``O`` blancas), para terminales sin colores.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable

from .game import (
    BLACK,
    EMPTY,
    WHITE,
    GameState,
    Move,
    apply_move,
    color_name,
    flips,
    initial_state,
    is_terminal,
    legal_moves,
    move_to_str,
    score,
    str_to_move,
    winner,
)

ANCHO = 52  # columnas del marco
COLUMNAS = "abcdefgh"

# Colores de 256 tonos (los admiten Windows Terminal, VS Code y casi cualquier terminal).
VERDE_CLARO = "48;5;34"
VERDE_OSCURO = "48;5;28"
DORADO = "48;5;178"  # casilla de la última jugada
TINTA_NEGRA = "38;5;16"
TINTA_BLANCA = "38;5;231"
TINTA_PISTA = "38;5;226"
NEGRITA = "1"
TENUE = "2"

# Una ficha ocupa dos líneas y seis columnas: con los bloques parece un disco.
DISCO_ARRIBA = " ▄██▄ "
DISCO_ABAJO = " ▀██▀ "
VACIA = "      "
PISTA_ARRIBA = "  ◆◆  "


def _estilo(texto: str, *codigos: str, color: bool) -> str:
    """Envuelve ``texto`` en códigos ANSI, o lo devuelve igual si no hay color."""
    if not color or not codigos:
        return texto
    return f"\x1b[{';'.join(codigos)}m{texto}\x1b[0m"


def _casilla_plana(valor: int, es_jugada: bool, es_ultima: bool) -> str:
    """Casilla de tres caracteres en ASCII: ``X``, ``O``, ``+`` (jugada posible) o ``.``."""
    simbolo = {EMPTY: "+" if es_jugada else ".", BLACK: "X", WHITE: "O"}[valor]
    return f"[{simbolo}]" if es_ultima else f" {simbolo} "


def _casilla_color(
    valor: int, es_jugada: bool, es_ultima: bool, fila: int, col: int
) -> tuple[str, str]:
    """Las dos líneas de una casilla con color."""
    fondo = DORADO if es_ultima else (VERDE_CLARO if (fila + col) % 2 == 0 else VERDE_OSCURO)
    if valor == EMPTY:
        if es_jugada:
            arriba = _estilo(PISTA_ARRIBA, TINTA_PISTA, NEGRITA, fondo, color=True)
        else:
            arriba = _estilo(VACIA, fondo, color=True)
        return arriba, _estilo(VACIA, fondo, color=True)
    tinta = TINTA_NEGRA if valor == BLACK else TINTA_BLANCA
    return (
        _estilo(DISCO_ARRIBA, tinta, fondo, color=True),
        _estilo(DISCO_ABAJO, tinta, fondo, color=True),
    )


def _tablero_plano(state: GameState, ultima: Move | None, posibles: set[Move]) -> str:
    cabecera = "".join(f" {letra} " for letra in COLUMNAS)
    lineas = [f"     {cabecera}"]
    for fila in range(8):
        celdas = "".join(
            _casilla_plana(state.board[fila][col], (fila, col) in posibles, (fila, col) == ultima)
            for col in range(8)
        )
        lineas.append(f"   {fila + 1}  {celdas}")
    return "\n".join(lineas)


def _tablero_color(state: GameState, ultima: Move | None, posibles: set[Move]) -> str:
    cabecera = "".join(f"  {letra}   " for letra in COLUMNAS)
    lineas = [_estilo(f"     {cabecera}", TENUE, color=True)]
    for fila in range(8):
        arriba, abajo = [], []
        for col in range(8):
            casilla_arriba, casilla_abajo = _casilla_color(
                state.board[fila][col], (fila, col) in posibles, (fila, col) == ultima, fila, col
            )
            arriba.append(casilla_arriba)
            abajo.append(casilla_abajo)
        numero = _estilo(f"{fila + 1}", TENUE, color=True)
        lineas.append(f"   {numero}  {''.join(arriba)}")
        lineas.append(f"      {''.join(abajo)}")
    return "\n".join(lineas)


def dibujar_tablero(state: GameState, ultima: Move | None = None, color: bool = False) -> str:
    """Devuelve el tablero como texto, marcando las jugadas posibles y la última jugada.

    Con ``color=False`` usa solo ASCII (``X`` negras, ``O`` blancas, ``+`` jugada posible
    y corchetes en la última jugada), para terminales sin colores o para redirigir a un
    archivo.

    Args:
        state: la posición a dibujar.
        ultima: la última jugada, que se resalta. ``None`` si no hay ninguna.
        color: si es ``True``, usa colores ANSI y fichas grandes.

    Returns:
        El tablero, con cabecera de columnas y número de fila, en varias líneas.
    """
    posibles = set(legal_moves(state))
    dibujo = _tablero_color if color else _tablero_plano
    return dibujo(state, ultima, posibles)


def _ficha(jugador: int, color: bool) -> str:
    """Nombre del color con su ficha: ``negras (X)`` o, con color, un bloque del color."""
    nombre = color_name(jugador)
    if not color:
        return f"{nombre} ({'X' if jugador == BLACK else 'O'})"
    tinta = TINTA_NEGRA if jugador == BLACK else TINTA_BLANCA
    return f"{nombre} {_estilo(' ██ ', tinta, VERDE_CLARO, color=True)}"


def _marcador(state: GameState, color: bool) -> str:
    negras, blancas = score(state)
    return (
        f"     {_ficha(BLACK, color)} {_estilo(f'{negras:>2}', NEGRITA, color=color)}"
        f"      {_ficha(WHITE, color)} {_estilo(f'{blancas:>2}', NEGRITA, color=color)}"
    )


def _titulo(color: bool) -> str:
    texto = "R E V E R S I   B O U N T Y"
    marco = ("═" if color else "=") * ANCHO
    return "\n".join(
        [
            "",
            _estilo(f"  {marco}", NEGRITA, color=color),
            _estilo(f"  {texto:^{ANCHO}}", NEGRITA, color=color),
            _estilo(f"  {marco}", NEGRITA, color=color),
        ]
    )


def _inicio_breve(color: bool) -> str:
    """Dos líneas al empezar: qué escribir y cómo pedir la ayuda completa."""
    pista = "◆◆" if color else "+"
    return "\n".join(
        [
            "",
            f"  Escribe una casilla marcada con {pista}, por ejemplo d3, y pulsa Enter.",
            "  ? ayuda completa    q salir",
        ]
    )


def _instrucciones(color: bool) -> str:
    """Ayuda completa (comando ``?``): cómo se juega, para quien no conoce el juego."""
    pista = "◆◆ amarillos" if color else "el símbolo +"
    lineas = [
        "",
        _estilo("  CÓMO SE JUEGA", NEGRITA, color=color),
        "",
        "  Es una partida para dos personas que se turnan en este mismo teclado.",
        "  Empiezan las negras. Gana quien tenga más fichas al terminar.",
        "",
        _estilo("  En tu turno:", NEGRITA, color=color),
        "    1. Mira el tablero: las columnas son letras (a-h) y las filas, números (1-8).",
        f"    2. Las casillas donde puedes jugar están marcadas con {pista}.",
        "    3. Escribe una de ellas, por ejemplo  d3,  y pulsa Enter.",
        "",
        _estilo("  Qué pasa al jugar:", NEGRITA, color=color),
        "    - Tu ficha encierra las del rival en línea recta contra otra tuya,",
        "      y todas las encerradas se dan la vuelta y pasan a ser tuyas.",
        "    - Si no tienes ninguna jugada posible, pasas el turno (el juego te avisa).",
        "    - La partida acaba cuando ninguno de los dos puede mover.",
        "",
        _estilo("  Comandos:", NEGRITA, color=color),
        "    ?   ver estas instrucciones otra vez",
        "    q   salir de la partida",
        "",
    ]
    return "\n".join(lineas)


def _pantalla(state: GameState, ultima: Move | None, color: bool) -> str:
    return "\n".join(["", dibujar_tablero(state, ultima, color), "", _marcador(state, color), ""])


def _anunciar_final(state: GameState, color: bool) -> str:
    negras, blancas = score(state)
    ganador = winner(state)
    if ganador == 0:
        veredicto = f"Empate a {negras}."
    else:
        mayor, menor = max(negras, blancas), min(negras, blancas)
        veredicto = f"Ganan las {color_name(ganador or BLACK)}, {mayor} a {menor}."
    marco = ("─" if color else "-") * ANCHO
    return "\n".join(
        [
            "",
            _estilo(f"  {marco}", TENUE, color=color),
            _estilo(f"  Fin de la partida. {veredicto}", NEGRITA, color=color),
            _estilo(f"  {marco}", TENUE, color=color),
            "",
        ]
    )


def jugar(
    leer: Callable[[str], str] = input,
    escribir: Callable[[str], object] = print,
    color: bool = False,
) -> GameState:
    """Juega una partida completa entre dos personas y devuelve el último estado.

    La partida termina al llegar a una posición terminal o si se escribe ``q`` (o se
    cierra la entrada). El paso de turno lo gestiona el motor: aquí solo se avisa.

    Args:
        leer: función que muestra un texto y devuelve lo que escribe quien juega.
        escribir: función que muestra un texto.
        color: si es ``True``, usa colores ANSI y fichas grandes.

    Returns:
        El estado en el que acabó la partida, o en el que se abandonó.
    """
    escribir(_titulo(color))
    escribir(_inicio_breve(color))

    state = initial_state()
    ultima: Move | None = None
    while not is_terminal(state):
        escribir(_pantalla(state, ultima, color))
        jugadas = legal_moves(state)
        opciones = " ".join(move_to_str(m) for m in jugadas)
        pregunta = (
            f"  Turno de las {_ficha(state.player, color)}. Jugadas: {opciones}\n"
            "  Escribe una casilla (? ayuda, q salir) > "
        )
        try:
            texto = leer(pregunta).strip().lower()
        except EOFError:
            escribir("\n  Partida abandonada.")
            return state
        if texto in ("q", "quit", "salir"):
            escribir("  Partida abandonada.")
            return state
        if texto in ("?", "ayuda", "help"):
            escribir(_instrucciones(color))
            continue
        try:
            jugada = str_to_move(texto)
        except ValueError:
            escribir(
                f"  '{texto}' no es una casilla. "
                "Usa una letra de la a a la h y un número del 1 al 8."
            )
            continue
        if jugada not in jugadas:
            escribir(
                f"  {move_to_str(jugada)} no es una jugada legal: "
                "no encierra ninguna ficha rival."
            )
            continue

        quien = state.player
        volteadas = len(flips(state.board, quien, jugada))
        state = apply_move(state, jugada)
        ultima = jugada
        plural = "ficha" if volteadas == 1 else "fichas"
        escribir(
            f"  Las {color_name(quien)} juegan {move_to_str(jugada)} "
            f"y voltean {volteadas} {plural}."
        )
        if state.player == quien and not is_terminal(state):
            escribir(f"  Las {color_name(-quien)} no pueden mover y pasan el turno.")

    escribir(_pantalla(state, ultima, color))
    escribir(_anunciar_final(state, color))
    return state


def _preparar_consola() -> None:
    """Activa los códigos ANSI en la consola de Windows y fuerza UTF-8 para los bloques."""
    os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main_texto() -> int:
    """Comando ``reversi-play``: partida de solo texto."""
    jugar(color=False)
    return 0


def main_color() -> int:
    """Comando ``reversi-play-color``: partida con colores y fichas grandes."""
    _preparar_consola()
    jugar(color=True)
    return 0
