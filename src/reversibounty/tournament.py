"""El torneo: una liguilla entre todos los jugadores registrados.

Cada jugador se enfrenta a todos los demás, **con los dos colores** y durante varias rondas.
Las partidas se juegan con :func:`~reversibounty.match.play_game` sin modificarlo: el torneo
solo decide quién juega contra quién, envuelve a cada bot en una capa de protección y suma
los resultados.

Tres decisiones de diseño:

* **Un único número siembra todo.** La semilla de cada partida se calcula a partir de la
  semilla del torneo, la ronda y los dos jugadores. Así el mismo torneo da el mismo resultado
  dos veces seguidas, y añadir un bot nuevo no cambia las partidas que ya jugaban los demás.
* **Un bot malo solo se perjudica a sí mismo.** :class:`GuardedPlayer` pide cada jugada en un
  hilo aparte con tiempo límite, captura cualquier excepción (también ``sys.exit()``) y
  comprueba que el bot no ha tocado el estado que recibió. ``play_game`` ya valida la jugada y
  entrega una copia del estado; la capa añade lo que le falta. Ante cualquier infracción, el
  infractor pierde esa partida, el motivo queda registrado y el torneo sigue.
* **La clasificación es un archivo.** :func:`write_leaderboard` la guarda como JSON en
  ``results/leaderboard.json``, con todo lo que una página necesita para dibujar la tabla.

Limitación conocida: Python no puede detener un hilo. Un bot que se pasa del tiempo pierde la
partida y el torneo continúa, pero su hilo sigue vivo en segundo plano hasta que termina. Si
se queda en un bucle infinito, consume CPU y hace más lentas las partidas siguientes, aunque
no las detiene. Aislarlo del todo exigiría un proceso por bot.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

from .game import BLACK, WHITE, GameState, Move, move_to_str
from .manifest import load_players
from .match import GameResult, play_game
from .player import Player

#: Versión del formato de ``leaderboard.json``. Cambia si cambia la forma del archivo.
SCHEMA_VERSION = 1

DEFAULT_SEED = 0
DEFAULT_ROUNDS = 5
DEFAULT_TIME_LIMIT = 1.0
DEFAULT_OUTPUT = Path("results") / "leaderboard.json"

T = TypeVar("T")


# -- La capa de protección ------------------------------------------------- #


def call_with_time_limit(function: Callable[[], T], time_limit: float) -> T:
    """Ejecuta ``function`` en un hilo aparte y espera como mucho ``time_limit`` segundos.

    Args:
        function: lo que hay que ejecutar, sin argumentos.
        time_limit: segundos de espera.

    Returns:
        Lo que devuelva ``function``.

    Raises:
        TimeoutError: si no termina a tiempo.
        Exception: la misma excepción que lance ``function``. Si lanza algo que no es una
            ``Exception`` (como ``SystemExit``), se convierte en ``RuntimeError`` para que no
            pueda cerrar el torneo.
    """
    salida: dict[str, Any] = {}

    def ejecutar() -> None:
        try:
            salida["valor"] = function()
        except BaseException as error:  # código ajeno: también sys.exit() o KeyboardInterrupt
            salida["error"] = error

    hilo = threading.Thread(target=ejecutar, daemon=True)
    hilo.start()
    hilo.join(time_limit)
    if hilo.is_alive():
        raise TimeoutError(f"no respondió en {time_limit:g} s")
    if "error" in salida:
        error = salida["error"]
        if isinstance(error, Exception):
            raise error
        raise RuntimeError(f"intentó terminar el programa con {type(error).__name__}") from error
    return salida["valor"]


class GuardedPlayer:
    """Envuelve a un jugador para que no pueda colgar ni estropear el torneo.

    Cumple lo que ``play_game`` espera de un jugador (un método ``choose_move``), así que el
    ejecutor de partidas no necesita saber que existe.

    Args:
        player: el jugador que se protege.
        time_limit: segundos que tiene para cada jugada.
    """

    def __init__(self, player: Player, time_limit: float) -> None:
        self._player = player
        self._time_limit = time_limit

    def choose_move(self, state: GameState) -> Move:
        """Pide la jugada al jugador protegido.

        Raises:
            TimeoutError: si no responde a tiempo.
            RuntimeError: si modifica el estado que recibe o intenta cerrar el programa.
            Exception: cualquier excepción que lance el jugador.
        """
        copia = replace(state)
        jugada = call_with_time_limit(lambda: self._player.choose_move(copia), self._time_limit)
        if copia != state:  # solo es posible saltándose el frozen, con object.__setattr__
            raise RuntimeError("modificó el estado que recibió")
        return jugada


# -- Resultados ------------------------------------------------------------ #


@dataclass(frozen=True)
class GameRecord:
    """Una partida del torneo.

    Attributes:
        round: número de ronda, desde 1.
        black: nombre del jugador con negras.
        white: nombre del jugador con blancas.
        black_seed: semilla con la que se creó el jugador de negras.
        white_seed: semilla con la que se creó el jugador de blancas.
        result: el resultado que devolvió ``play_game``.
    """

    round: int
    black: str
    white: str
    black_seed: int
    white_seed: int
    result: GameResult

    @property
    def winner_name(self) -> str | None:
        """Nombre del ganador, o ``None`` si hubo empate."""
        if self.result.winner == BLACK:
            return self.black
        if self.result.winner == WHITE:
            return self.white
        return None

    def to_dict(self) -> dict[str, Any]:
        """La partida como diccionario serializable a JSON."""
        return {
            "round": self.round,
            "black": self.black,
            "white": self.white,
            "seeds": [self.black_seed, self.white_seed],
            "winner": self.winner_name,
            "score": list(self.result.score),
            "moves": [move_to_str(jugada) for jugada in self.result.moves],
            "forfeit": self.result.forfeit,
        }


@dataclass
class Standing:
    """Los totales de un jugador en el torneo.

    Attributes:
        name: nombre del jugador.
        icon: su emoji.
        authors: sus autores.
        description: su estrategia, en una frase.
        wins: partidas ganadas.
        draws: partidas empatadas.
        losses: partidas perdidas, incluidas las perdidas por infracción.
        forfeits: partidas perdidas por infringir las reglas.
        discs_for: fichas propias al final de cada partida, sumadas.
        discs_against: fichas del rival al final de cada partida, sumadas.
        forfeit_reasons: el motivo de cada partida perdida por infracción.
    """

    name: str
    icon: str
    authors: list[str]
    description: str
    wins: int = 0
    draws: int = 0
    losses: int = 0
    forfeits: int = 0
    discs_for: int = 0
    discs_against: int = 0
    forfeit_reasons: list[str] = field(default_factory=list)

    @property
    def played(self) -> int:
        """Partidas jugadas."""
        return self.wins + self.draws + self.losses

    @property
    def points(self) -> float:
        """Puntos: 1 por victoria, 0,5 por empate y 0 por derrota."""
        return self.wins + self.draws / 2

    @property
    def disc_diff(self) -> int:
        """Diferencia de fichas: el primer desempate."""
        return self.discs_for - self.discs_against

    def to_dict(self, rank: int) -> dict[str, Any]:
        """Los totales como diccionario serializable a JSON, con su puesto."""
        return {
            "rank": rank,
            "name": self.name,
            "icon": self.icon,
            "authors": list(self.authors),
            "description": self.description,
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "forfeits": self.forfeits,
            "points": self.points,
            "discs_for": self.discs_for,
            "discs_against": self.discs_against,
            "disc_diff": self.disc_diff,
            "forfeit_reasons": sorted(set(self.forfeit_reasons)),
        }


@dataclass(frozen=True)
class TournamentResult:
    """El resultado completo de un torneo.

    Attributes:
        seed: el número del que sale toda la aleatoriedad.
        rounds: rondas jugadas; en cada una, cada pareja juega una vez con cada color.
        time_limit: segundos por jugada.
        standings: la clasificación, de primero a último.
        games: todas las partidas, en el orden en que se jugaron.
        finished_at: cuándo terminó, en ISO 8601 y UTC.
    """

    seed: int
    rounds: int
    time_limit: float
    standings: list[Standing]
    games: list[GameRecord]
    finished_at: str

    def to_dict(self) -> dict[str, Any]:
        """El torneo en el formato de ``leaderboard.json``."""
        return {
            "schema_version": SCHEMA_VERSION,
            "finished_at": self.finished_at,
            "seed": self.seed,
            "rounds": self.rounds,
            "time_limit": self.time_limit,
            "standings": [
                standing.to_dict(rank) for rank, standing in enumerate(self.standings, start=1)
            ],
            "games": [game.to_dict() for game in self.games],
        }


# -- El torneo ------------------------------------------------------------- #


def game_seeds(seed: int, round_number: int, black: str, white: str) -> tuple[int, int]:
    """Las semillas de los dos jugadores en una partida concreta.

    Dependen solo de la semilla del torneo, la ronda y los nombres, no del orden en que se
    juegan las partidas ni de qué otros jugadores haya.
    """
    rng = random.Random(f"{seed}/{round_number}/{black}/{white}")
    return rng.getrandbits(32), rng.getrandbits(32)


def _prepare(
    cls: type[Player], name: str, seed: int, time_limit: float
) -> GuardedPlayer | str:
    """Crea un jugador protegido para una partida, o devuelve el motivo por el que no se pudo."""
    try:
        declarado = call_with_time_limit(cls.get_name, time_limit)
        if declarado != name:
            return f"cambió su nombre a {declarado!r}"
        jugador = call_with_time_limit(lambda: cls.create(seed), time_limit)
    except Exception as error:  # código ajeno: cualquier fallo es una derrota
        return f"no se pudo crear: {type(error).__name__}: {error}"
    return GuardedPlayer(jugador, time_limit)


def _play_one(
    players: Mapping[str, type[Player]],
    black: str,
    white: str,
    seeds: tuple[int, int],
    time_limit: float,
) -> GameResult:
    """Juega una partida con ``play_game``, o la da por perdida si un jugador no se puede crear."""
    negras = _prepare(players[black], black, seeds[0], time_limit)
    blancas = _prepare(players[white], white, seeds[1], time_limit)
    if isinstance(negras, GuardedPlayer) and isinstance(blancas, GuardedPlayer):
        return play_game(negras, blancas)
    motivos = []
    if isinstance(negras, str):
        motivos.append(f"las negras {negras}")
    if isinstance(blancas, str):
        motivos.append(f"las blancas {blancas}")
    ganador = 0 if len(motivos) == 2 else (WHITE if isinstance(negras, str) else BLACK)
    return GameResult(winner=ganador, moves=(), score=(2, 2), forfeit="; ".join(motivos))


def _add(standing: Standing, mine: int, theirs: int, outcome: int, forfeit: str | None) -> None:
    """Suma una partida a los totales de un jugador.

    ``outcome`` vale 1 si ganó, 0 si empató y -1 si perdió. ``forfeit`` es el motivo de la
    infracción, si la hubo: solo cuenta para quien perdió.
    """
    standing.discs_for += mine
    standing.discs_against += theirs
    if outcome > 0:
        standing.wins += 1
    elif outcome == 0:
        standing.draws += 1
    else:
        standing.losses += 1
        if forfeit is not None:
            standing.forfeits += 1
            standing.forfeit_reasons.append(forfeit)


def run_tournament(
    players: Mapping[str, type[Player]] | None = None,
    *,
    seed: int = DEFAULT_SEED,
    rounds: int = DEFAULT_ROUNDS,
    time_limit: float = DEFAULT_TIME_LIMIT,
) -> TournamentResult:
    """Juega la liguilla completa y devuelve la clasificación y el detalle de cada partida.

    Args:
        players: ``nombre -> clase``, como lo devuelve
            :func:`~reversibounty.manifest.load_players`. Por defecto, los registrados.
        seed: el único número del que sale toda la aleatoriedad.
        rounds: cuántas veces juega cada pareja con cada color.
        time_limit: segundos que tiene cada jugador para cada jugada.

    Returns:
        Un :class:`TournamentResult`. No imprime nada.

    Raises:
        ValueError: si ``rounds`` es menor que 1 o ``time_limit`` no es positivo.
    """
    if rounds < 1:
        raise ValueError("rounds debe ser al menos 1")
    if time_limit <= 0:
        raise ValueError("time_limit debe ser positivo")
    players = load_players() if players is None else players

    standings = {
        name: Standing(
            name=name,
            icon=cls.get_icon(),
            authors=list(cls.get_authors()),
            description=cls.get_description(),
        )
        for name, cls in players.items()
    }
    games: list[GameRecord] = []
    for round_number in range(1, rounds + 1):
        for black, white in itertools.permutations(players, 2):
            seeds = game_seeds(seed, round_number, black, white)
            result = _play_one(players, black, white, seeds, time_limit)
            games.append(GameRecord(round_number, black, white, *seeds, result))
            if result.winner == 0 and result.forfeit is not None:
                negro, blanco = -1, -1  # los dos infringieron: pierden los dos
            else:
                negro, blanco = result.winner * BLACK, result.winner * WHITE
            negras, blancas = result.score
            _add(standings[black], negras, blancas, negro, result.forfeit)
            _add(standings[white], blancas, negras, blanco, result.forfeit)

    ordenada = sorted(
        standings.values(), key=lambda s: (-s.points, -s.disc_diff, -s.wins, s.name)
    )
    return TournamentResult(
        seed=seed,
        rounds=rounds,
        time_limit=time_limit,
        standings=ordenada,
        games=games,
        finished_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


# -- Salida: tabla y archivo ----------------------------------------------- #


def format_table(result: TournamentResult) -> str:
    """La clasificación como tabla de texto, con los motivos de las infracciones debajo."""
    cabecera = f"{'#':>3}  {'Jugador':<24}{'PJ':>4}{'G':>4}{'E':>4}{'P':>4}{'Pts':>7}{'Dif':>6}{'Inf':>5}"
    lineas = [cabecera, "-" * len(cabecera)]
    for rank, s in enumerate(result.standings, start=1):
        jugador = f"{s.icon} {s.name}"
        lineas.append(
            f"{rank:>3}  {jugador:<24}{s.played:>4}{s.wins:>4}{s.draws:>4}{s.losses:>4}"
            f"{s.points:>7.1f}{s.disc_diff:>+6}{s.forfeits:>5}"
        )
    infractores = [s for s in result.standings if s.forfeits]
    if infractores:
        lineas += ["", "Partidas perdidas por infracción:"]
        for s in infractores:
            motivos = sorted(set(s.forfeit_reasons))
            lineas.append(f"  {s.name}: {s.forfeits} ({motivos[0]})")
            lineas += [f"  {' ' * len(s.name)}  ({motivo})" for motivo in motivos[1:]]
    return "\n".join(lineas)


def write_leaderboard(result: TournamentResult, path: str | Path = DEFAULT_OUTPUT) -> Path:
    """Guarda la clasificación en ``path`` como JSON, creando la carpeta si no existe.

    Escribe primero un archivo temporal y luego lo renombra, para que quien lo lea a la vez
    nunca vea un archivo a medias.

    Returns:
        La ruta del archivo escrito.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporal = path.with_name(path.name + ".tmp")
    texto = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    temporal.write_text(texto + "\n", encoding="utf-8")
    os.replace(temporal, path)
    return path


def main(argv: Sequence[str] | None = None) -> int:
    """Comando ``reversi-tournament``: juega el torneo, imprime la tabla y guarda el JSON."""
    parser = argparse.ArgumentParser(
        description="Juega una liguilla entre todos los jugadores registrados."
    )
    parser.add_argument(
        "--semilla", type=int, default=DEFAULT_SEED,
        help=f"número del que sale toda la aleatoriedad (por defecto, {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--rondas", type=int, default=DEFAULT_ROUNDS,
        help=f"partidas de cada pareja con cada color (por defecto, {DEFAULT_ROUNDS})",
    )
    parser.add_argument(
        "--limite", type=float, default=DEFAULT_TIME_LIMIT,
        help=f"segundos por jugada (por defecto, {DEFAULT_TIME_LIMIT:g})",
    )
    parser.add_argument(
        "--salida", type=Path, default=DEFAULT_OUTPUT,
        help=f"dónde guardar la clasificación (por defecto, {DEFAULT_OUTPUT.as_posix()})",
    )
    parser.add_argument(
        "--jugadores", type=Path, default=None,
        help="carpeta con builtin/ y custom/ (por defecto, players/ del repositorio)",
    )
    args = parser.parse_args(argv)
    if args.rondas < 1:
        parser.error("--rondas debe ser al menos 1")
    if args.limite <= 0:
        parser.error("--limite debe ser positivo")

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # los emojis, también en la consola de Windows
    result = run_tournament(
        load_players(args.jugadores), seed=args.semilla, rounds=args.rondas,
        time_limit=args.limite,
    )
    path = write_leaderboard(result, args.salida)
    print(format_table(result))
    print(f"\n{len(result.games)} partidas. Clasificación guardada en {path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
