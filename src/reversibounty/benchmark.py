"""Medir los bots: enfrenta parejas de jugadores y muestra sus tasas de victoria.

Cada pareja juega **en los dos sentidos**: la mitad de las partidas con cada jugador como
primero (negras) y la otra mitad como segundo (blancas). En el Reversi mover primero puede
valer más que cualquier cantidad de inteligencia, y un bot que solo se ha probado como
primero es un bot del que no se sabe nada.

La semilla es fija, así que una ejecución se repite igual, y el informe siempre dice cuántas
partidas se han jugado. Se lanza con::

    python -m reversibounty.benchmark
    python -m reversibounty.benchmark --partidas 40 --semilla 3
    python -m reversibounty.benchmark --jugadores Aleatorio Avaricioso
"""

from __future__ import annotations

import argparse
import itertools
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .game import BLACK, WHITE
from .manifest import load_players
from .match import play_game
from .player import Player
from .tournament import game_seeds

DEFAULT_GAMES = 20
DEFAULT_SEED = 0


@dataclass(frozen=True)
class PairResult:
    """El resultado de enfrentar al jugador A con el jugador B.

    Attributes:
        a: nombre del jugador A.
        b: nombre del jugador B.
        games: partidas jugadas (la mitad con A como primero y la mitad como segundo).
        a_wins: partidas ganadas por A.
        b_wins: partidas ganadas por B.
        draws: partidas empatadas.
        a_wins_first: victorias de A jugando con negras (primero).
        a_wins_second: victorias de A jugando con blancas (segundo).
    """

    a: str
    b: str
    games: int
    a_wins: int
    b_wins: int
    draws: int
    a_wins_first: int
    a_wins_second: int

    @property
    def a_rate(self) -> float:
        """Porcentaje de partidas ganadas por A (0-100)."""
        return 100 * self.a_wins / self.games

    @property
    def a_rate_first(self) -> float:
        """Porcentaje ganado por A cuando juega primero."""
        return 100 * self.a_wins_first / (self.games // 2)

    @property
    def a_rate_second(self) -> float:
        """Porcentaje ganado por A cuando juega segundo."""
        return 100 * self.a_wins_second / (self.games // 2)


def measure_pair(
    a: type[Player], b: type[Player], games: int = DEFAULT_GAMES, seed: int = DEFAULT_SEED
) -> PairResult:
    """Juega ``games`` partidas entre A y B, la mitad con cada color.

    Args:
        a: clase del jugador A.
        b: clase del jugador B.
        games: número de partidas; tiene que ser par y al menos 2.
        seed: semilla de la que sale toda la aleatoriedad.

    Raises:
        ValueError: si ``games`` no es par o es menor que 2.
    """
    if games < 2 or games % 2:
        raise ValueError("games debe ser par y al menos 2, para jugar mitad con cada color")
    name_a, name_b = a.get_name(), b.get_name()
    a_wins = b_wins = draws = a_first = a_second = 0
    for number in range(1, games // 2 + 1):
        # Con A de negras (primero).
        seed_a, seed_b = game_seeds(seed, number, name_a, name_b)
        winner = play_game(a.create(seed_a), b.create(seed_b)).winner
        if winner == BLACK:
            a_wins += 1
            a_first += 1
        elif winner == WHITE:
            b_wins += 1
        else:
            draws += 1
        # Con A de blancas (segundo).
        seed_b, seed_a = game_seeds(seed, number, name_b, name_a)
        winner = play_game(b.create(seed_b), a.create(seed_a)).winner
        if winner == WHITE:
            a_wins += 1
            a_second += 1
        elif winner == BLACK:
            b_wins += 1
        else:
            draws += 1
    return PairResult(name_a, name_b, games, a_wins, b_wins, draws, a_first, a_second)


def measure_all(
    players: Mapping[str, type[Player]], games: int = DEFAULT_GAMES, seed: int = DEFAULT_SEED
) -> list[PairResult]:
    """Enfrenta a todas las parejas de ``players`` y devuelve un resultado por pareja."""
    return [
        measure_pair(players[a], players[b], games, seed)
        for a, b in itertools.combinations(players, 2)
    ]


def format_table(results: Sequence[PairResult], seed: int = DEFAULT_SEED) -> str:
    """La tabla de tasas de victoria, con el número de partidas y la semilla."""
    if not results:
        return "No hay parejas que medir."
    cabecera = (
        f"{'Jugador A':<18}{'Jugador B':<18}{'Partidas':>9}{'Gana A':>9}{'Gana B':>9}"
        f"{'Empates':>9}{'A 1º':>8}{'A 2º':>8}"
    )
    lineas = [f"Tasas de victoria de A (semilla {seed})", cabecera, "-" * len(cabecera)]
    for r in results:
        lineas.append(
            f"{r.a:<18}{r.b:<18}{r.games:>9}{r.a_rate:>8.1f}%{100 * r.b_wins / r.games:>8.1f}%"
            f"{r.draws:>9}{r.a_rate_first:>7.0f}%{r.a_rate_second:>7.0f}%"
        )
    lineas += ["", "A 1º / A 2º: % de victorias de A cuando juega primero / segundo."]
    for r in results:
        lineas.append(
            f"{r.a} gana el {r.a_rate:.0f}% de {r.games} partidas contra {r.b}, "
            f"y el {r.a_rate_second:.0f}% cuando juega en segundo lugar."
        )
    return "\n".join(lineas)


def main(argv: Sequence[str] | None = None) -> int:
    """Comando de medición: juega las parejas, imprime la tabla y devuelve 0."""
    parser = argparse.ArgumentParser(
        description="Mide las tasas de victoria entre bots, jugando en los dos sentidos."
    )
    parser.add_argument(
        "--partidas", type=int, default=DEFAULT_GAMES,
        help=f"partidas por pareja, par (por defecto, {DEFAULT_GAMES})",
    )
    parser.add_argument(
        "--semilla", type=int, default=DEFAULT_SEED,
        help=f"número del que sale toda la aleatoriedad (por defecto, {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--jugadores", nargs="+", default=None,
        help="nombres de los jugadores a medir (por defecto, todos los registrados)",
    )
    args = parser.parse_args(argv)
    if args.partidas < 2 or args.partidas % 2:
        parser.error("--partidas debe ser par y al menos 2")

    registrados = load_players()
    if args.jugadores is None:
        elegidos = registrados
    else:
        # Los nombres empiezan por mayúscula, pero en la terminal se aceptan escritos como sea.
        por_nombre = {nombre.casefold(): nombre for nombre in registrados}
        desconocidos = [n for n in args.jugadores if n.casefold() not in por_nombre]
        if desconocidos:
            parser.error(f"jugadores desconocidos: {', '.join(desconocidos)}")
        nombres = [por_nombre[n.casefold()] for n in args.jugadores]
        elegidos = {n: registrados[n] for n in nombres}
    if len(elegidos) < 2:
        parser.error("hacen falta al menos dos jugadores")

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(format_table(measure_all(elegidos, args.partidas, args.semilla), args.semilla))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
