"""Puente entre la web y el motor de Python. En el navegador se ejecuta con Pyodide.

La página no conoce ninguna regla del Reversi: las jugadas legales, los volteos, los pasos de
turno, el final y los bots salen del mismo paquete ``reversibounty`` que usan los tests y el
torneo. JavaScript solo pregunta y dibuja la respuesta.

* Todo cruza la frontera como texto JSON, en los dos sentidos. Así se puede probar desde
  pytest sin navegador y no depende de cómo convierte Pyodide los objetos entre lenguajes.
* La respuesta siempre tiene la misma forma: ``{"ok": true, "result": ...}`` o
  ``{"ok": false, "error": "mensaje"}``. Ni una entrada mala ni un fallo inesperado de Python
  llegan a JavaScript como excepción: llegan como ``ok: false``.
* Las funciones son pequeñas y no tienen reglas propias: traducen de JSON al motor, llaman al
  motor y traducen la respuesta de vuelta.
* La lista de rivales sale del registro (:func:`reversibounty.manifest.load_players`): un bot
  nuevo aparece solo en la web. La carpeta se pasa a :func:`init` porque dentro del navegador
  el paquete no está en el repositorio y la ruta por defecto del registro no existe.
* Un bot que falla pierde y la web sigue, con la misma regla que ``play_game`` (ver
  :func:`bot_move`).

Las funciones que puede llamar la página están en ``__all__``.
"""

from __future__ import annotations

import functools
import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from reversibounty import game
from reversibounty.manifest import ManifestError, load_players
from reversibounty.match import Forfeit, request_move
from reversibounty.player import Player

__all__ = [
    "bot_move",
    "init",
    "legal_moves",
    "new_game",
    "play_move",
    "players",
    "start_game",
    "start_match",
    "view",
]


class BridgeError(ValueError):
    """Una petición que el puente no puede atender: entrada mal formada o fuera de turno."""


@dataclass
class _Partida:
    """Los bots de la partida en curso, uno por color: ``color -> (nombre, bot)``.

    Puede haber dos (bot contra bot), uno (persona contra bot) o ninguno (dos personas: el puente
    solo hace falta para las reglas). Se crean una vez por partida, como en el torneo.
    """

    bots: dict[int, tuple[str, Player]]


#: Jugadores admitidos en el registro, ``nombre -> clase``. Los rellena :func:`init`.
_JUGADORES: dict[str, type[Player]] = {}
#: La partida en curso, o ``None`` si todavía no se ha llamado a :func:`start_game`.
_PARTIDA: _Partida | None = None


# ------------------------------------------------------------------ la frontera --- #


def _puente(fn: Callable[..., Any]) -> Callable[..., str]:
    """Convierte una función de Python en una función de la frontera JSON.

    Descodifica cada argumento desde JSON, comprueba cuántos llegan, llama a ``fn`` y
    envuelve lo que devuelve (o el error) en ``{"ok": ..., "result"/"error": ...}``. Toda
    la gestión de errores está aquí, en un solo sitio, para que ninguna función pública
    pueda olvidarla.
    """
    firma = inspect.signature(fn)

    @functools.wraps(fn)
    def envoltura(*args: str) -> str:
        try:
            valores = [_leer_json(texto, posicion) for posicion, texto in enumerate(args, 1)]
            try:
                firma.bind(*valores)
            except TypeError:
                raise BridgeError(
                    f"{fn.__name__} espera {len(firma.parameters)} argumentos y ha recibido "
                    f"{len(valores)}"
                ) from None
            respuesta = {"ok": True, "result": fn(*valores)}
        except BridgeError as error:
            respuesta = {"ok": False, "error": str(error)}
        except Exception as error:  # un fallo nuestro tampoco debe romper la página
            respuesta = {
                "ok": False,
                "error": f"error interno en {fn.__name__}: {type(error).__name__}: {error}",
            }
        return json.dumps(respuesta, ensure_ascii=False)

    return envoltura


def _leer_json(texto: object, posicion: int) -> Any:
    """Descodifica un argumento. Un texto que no es JSON es un error de quien llama."""
    if not isinstance(texto, str):
        raise BridgeError(f"el argumento {posicion} debe llegar como texto JSON")
    try:
        return json.loads(texto)
    except json.JSONDecodeError as error:
        raise BridgeError(f"el argumento {posicion} no es JSON válido: {error.msg}") from None


def _estado(valor: object) -> game.GameState:
    """Un estado en el formato de :meth:`GameState.to_dict`, validado por el propio motor."""
    if not isinstance(valor, dict):
        raise BridgeError("el estado debe ser un objeto con 'board' y 'player'")
    try:
        return game.GameState.from_dict(valor)
    except ValueError as error:
        raise BridgeError(f"estado no válido: {error}") from None


def _jugada(valor: object) -> game.Move:
    """Una jugada como ``[fila, columna]`` o en notación, como ``"d3"``.

    Aquí solo se comprueba la forma; si la jugada es legal lo decide el motor.
    """
    if isinstance(valor, str):
        try:
            return game.str_to_move(valor)
        except ValueError as error:
            raise BridgeError(str(error)) from None
    if (
        isinstance(valor, list)
        and len(valor) == 2
        and all(isinstance(x, int) and not isinstance(x, bool) for x in valor)
    ):
        return valor[0], valor[1]
    raise BridgeError(f"una jugada debe ser [fila, columna] o un texto como 'd3', no {valor!r}")


def _entero(valor: object, nombre: str) -> int:
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise BridgeError(f"{nombre} debe ser un número entero, no {valor!r}")
    return valor


# ---------------------------------------------------------------- descripciones --- #


def _vista(state: game.GameState) -> dict[str, Any]:
    """Todo lo que la página necesita para dibujar una posición, calculado por el motor.

    ``over`` dice si la partida ha terminado, sea porque nadie puede mover o porque un bot
    ha perdido por incumplir las reglas (ver :func:`bot_move`). Cuando ha terminado, ``turn``
    es ``None``: en una posición terminal el color que guarda el estado no significa nada
    (ver :class:`~reversibounty.game.GameState`).
    """
    over = game.is_terminal(state)
    negras, blancas = game.score(state)
    return {
        "state": state.to_dict(),
        "turn": None if over else state.player,
        "legal": [list(jugada) for jugada in game.legal_moves(state)],
        "score": [negras, blancas],
        "over": over,
        "winner": game.winner(state),
        "forfeit": None,
    }


def _jugar(antes: game.GameState, jugada: game.Move) -> dict[str, Any]:
    """Aplica una jugada con el motor y describe lo que ha pasado.

    Las fichas volteadas son las casillas que cambian de color entre el tablero de antes y el
    de después (la casilla donde se juega estaba vacía, así que no cuenta): la página puede
    animarlas sin que el puente calcule nada por su cuenta. ``passed`` vale ``True`` si el
    rival no tenía jugadas y el motor ha devuelto el turno a quien acaba de mover.
    """
    try:
        despues = game.apply_move(antes, jugada)
    except ValueError as error:  # el motor es quien decide si una jugada es legal
        raise BridgeError(str(error)) from None
    volteadas = [
        [fila, columna]
        for fila in range(game.SIZE)
        for columna in range(game.SIZE)
        if antes.board[fila][columna] not in (game.EMPTY, despues.board[fila][columna])
    ]
    vista = _vista(despues)
    vista.update(
        move=list(jugada),
        notation=game.move_to_str(jugada),
        mover=antes.player,
        flipped=volteadas,
        passed=not vista["over"] and despues.player == antes.player,
    )
    return vista


def _ficha(cls: type[Player]) -> dict[str, Any]:
    """La identidad pública de un jugador, tal como la declara su clase."""
    return {
        "name": cls.get_name(),
        "icon": cls.get_icon(),
        "authors": cls.get_authors(),
        "description": cls.get_description(),
    }


# ------------------------------------------------------------------- jugadores --- #


@_puente
def init(players_dir: object) -> list[dict[str, Any]]:
    """Carga el registro de jugadores de ``players_dir`` y devuelve sus identidades.

    Se llama una vez, al arrancar. La carpeta es explícita porque en el navegador el
    paquete se descomprime de ``py.zip`` y la ruta por defecto del registro no existe.
    """
    global _JUGADORES, _PARTIDA
    if not isinstance(players_dir, str) or not players_dir:
        raise BridgeError("players_dir debe ser la ruta de la carpeta players/")
    try:
        _JUGADORES = load_players(players_dir)
    except ManifestError as error:
        raise BridgeError(f"no se pudo cargar el registro de jugadores: {error}") from None
    _PARTIDA = None
    return [_ficha(cls) for cls in _JUGADORES.values()]


@_puente
def players() -> list[dict[str, Any]]:
    """Las identidades de los jugadores cargados por :func:`init`, en orden de admisión."""
    if not _JUGADORES:
        raise BridgeError("no hay jugadores cargados: llama antes a init")
    return [_ficha(cls) for cls in _JUGADORES.values()]


# --------------------------------------------------------------------- partidas --- #


@_puente
def new_game() -> dict[str, Any]:
    """La posición inicial, descrita con :func:`_vista`."""
    return _vista(game.initial_state())


@_puente
def view(state: object) -> dict[str, Any]:
    """Describe una posición. Sirve para validar y retomar una partida guardada."""
    return _vista(_estado(state))


@_puente
def legal_moves(state: object) -> list[list[int]]:
    """Las jugadas legales de quien mueve, como ``[fila, columna]``."""
    return [list(jugada) for jugada in game.legal_moves(_estado(state))]


@_puente
def play_move(state: object, move: object) -> dict[str, Any]:
    """Aplica una jugada (la de la persona) y describe la posición resultante.

    Devuelve un error claro si la jugada está mal escrita o no es legal: la página no
    debería mandarla nunca, pero el puente no se fía.
    """
    antes = _estado(state)
    if game.is_terminal(antes):
        raise BridgeError("la partida ya ha terminado")
    return _jugar(antes, _jugada(move))


# ------------------------------------------------------------------------- bots --- #


def _crear_bot(nombre: object, semilla: int) -> tuple[str, Player]:
    """El bot con ese nombre, creado con ``create(semilla)``; un error claro si no se puede."""
    if not _JUGADORES:
        raise BridgeError("no hay jugadores cargados: llama antes a init")
    if not isinstance(nombre, str) or nombre not in _JUGADORES:
        disponibles = ", ".join(_JUGADORES)
        raise BridgeError(f"no hay ningún jugador llamado {nombre!r}; los hay: {disponibles}")
    try:
        return nombre, _JUGADORES[nombre].create(seed=semilla)
    except Exception as error:  # código ajeno: lo contamos, no lo dejamos escapar
        raise BridgeError(f"{nombre} no se pudo crear: {type(error).__name__}: {error}") from None


@_puente
def start_game(bot: object, bot_color: object, seed: object) -> dict[str, Any]:
    """Crea el bot rival de una partida nueva, con ``create(seed)`` como en el torneo.

    La semilla la elige la página y la guarda: si alguien recarga a mitad de partida, la
    página vuelve a llamar aquí con la misma semilla y sigue desde la posición guardada.
    """
    global _PARTIDA
    color = _entero(bot_color, "bot_color")
    if color not in (game.BLACK, game.WHITE):
        raise BridgeError("bot_color debe ser 1 (negras) o -1 (blancas)")
    semilla = _entero(seed, "seed")
    nombre, jugador = _crear_bot(bot, semilla)
    _PARTIDA = _Partida(bots={color: (nombre, jugador)})
    return {"bot": _ficha(_JUGADORES[nombre]), "bot_color": color}


@_puente
def start_match(black: object, white: object, seed: object) -> dict[str, Any]:
    """Prepara una partida en la que cada color lo juega un bot, o nadie (una persona).

    ``black`` y ``white`` son el nombre de un bot o ``None`` si ese lado lo juega una persona. Con
    dos bots, cada uno se crea con su propia semilla (``seed`` para las negras y ``seed + 1`` para
    las blancas), así que dos bots iguales no juegan idéntico y la partida se puede repetir.
    """
    global _PARTIDA
    semilla = _entero(seed, "seed")
    bots: dict[int, tuple[str, Player]] = {}
    for color, nombre, desplazamiento in ((game.BLACK, black, 0), (game.WHITE, white, 1)):
        if nombre is not None:
            bots[color] = _crear_bot(nombre, semilla + desplazamiento)
    _PARTIDA = _Partida(bots=bots)
    return {
        "black": _ficha(_JUGADORES[bots[game.BLACK][0]]) if game.BLACK in bots else None,
        "white": _ficha(_JUGADORES[bots[game.WHITE][0]]) if game.WHITE in bots else None,
    }


@_puente
def bot_move(state: object) -> dict[str, Any]:
    """Pide su jugada al bot de la partida en curso y la aplica.

    La jugada se pide con :func:`~reversibounty.match.request_move`, la misma regla que usa
    :func:`~reversibounty.match.play_game`. Si el bot lanza una excepción o devuelve una jugada
    ilegal, pierde la partida: la respuesta trae ``over: true``, el ganador y el motivo en
    ``forfeit``. No es un error del puente, es un resultado de la partida.
    """
    if _PARTIDA is None:
        raise BridgeError("no hay ninguna partida: llama antes a start_game")
    antes = _estado(state)
    if game.is_terminal(antes):
        raise BridgeError("la partida ya ha terminado")
    if antes.player not in _PARTIDA.bots:
        raise BridgeError("no es el turno de un bot")
    nombre, bot = _PARTIDA.bots[antes.player]
    try:
        jugada = request_move(bot, antes)
    except Forfeit as forfeit:
        return _abandono(antes.player, nombre, antes, forfeit.reason)
    return _jugar(antes, jugada)


def _abandono(color: int, nombre: str, state: game.GameState, motivo: str) -> dict[str, Any]:
    """La partida termina porque un bot ha incumplido las reglas: gana el otro lado."""
    vista = _vista(state)
    vista.update(
        turn=None,
        legal=[],
        over=True,
        winner=game.opponent(color),
        forfeit=f"{nombre} {motivo}",
    )
    return vista
