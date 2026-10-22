"""Tests del torneo (paso 5): emparejamientos, semilla, bots rotos y leaderboard.json."""

from __future__ import annotations

import io
import json
from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime

import pytest

from bots_rotos import (
    CambiaDeNombre,
    LanzaExcepcion,
    ModificaAEscondidas,
    ModificaElTablero,
    SaleDelPrograma,
    SeCuelga,
)
from reversibounty import GameState, Move, Player, legal_moves, play_game, str_to_move
from reversibounty.bots import GreedyPlayer, RandomPlayer
from reversibounty.tournament import (
    SCHEMA_VERSION,
    GuardedPlayer,
    format_table,
    main,
    run_tournament,
    write_leaderboard,
)

LIMITE = 0.2  # segundos por jugada en los tests: de sobra para los bots de referencia


def registro(*clases: type[Player]) -> dict[str, type[Player]]:
    """Un registro ``nombre -> clase``, como el que devuelve ``load_players``."""
    return {cls.get_name(): cls for cls in clases}


def sin_hora(resultado) -> dict:
    """El JSON del torneo sin la hora, que es lo único que cambia entre dos ejecuciones."""
    datos = resultado.to_dict()
    del datos["finished_at"]
    return datos


def puesto(resultado, nombre: str):
    return next(s for s in resultado.standings if s.name == nombre)


# -- 5.1 Todos los emparejamientos ----------------------------------------- #


def test_cada_pareja_juega_con_los_dos_colores_en_cada_ronda():
    jugadores = registro(RandomPlayer, GreedyPlayer, CambiaDeNombre)
    resultado = run_tournament(jugadores, rounds=2, time_limit=LIMITE)
    parejas = Counter((g.black, g.white) for g in resultado.games)
    assert len(resultado.games) == 3 * 2 * 2  # parejas ordenadas x rondas
    assert set(parejas) == {(a, b) for a in jugadores for b in jugadores if a != b}
    assert set(parejas.values()) == {2}


def test_los_totales_cuadran_con_el_detalle_de_las_partidas():
    resultado = run_tournament(registro(RandomPlayer, GreedyPlayer), rounds=3, time_limit=LIMITE)
    assert all(s.played == 6 for s in resultado.standings)
    ganadas = sum(s.wins for s in resultado.standings)
    perdidas = sum(s.losses for s in resultado.standings)
    empatadas = sum(s.draws for s in resultado.standings)
    assert ganadas == perdidas == sum(1 for g in resultado.games if g.winner_name)
    assert empatadas == 2 * sum(1 for g in resultado.games if g.winner_name is None)


def test_la_clasificacion_va_de_mas_a_menos_puntos():
    resultado = run_tournament(registro(RandomPlayer, GreedyPlayer), rounds=3, time_limit=LIMITE)
    puntos = [s.points for s in resultado.standings]
    assert puntos == sorted(puntos, reverse=True)
    assert resultado.standings[0].name == "avaricioso"  # gana con claridad al aleatorio


def test_las_partidas_son_las_mismas_que_daria_play_game():
    """El torneo no tiene un segundo ejecutor: cada partida es la de play_game."""
    jugadores = registro(RandomPlayer, GreedyPlayer)
    for g in run_tournament(jugadores, rounds=2, time_limit=LIMITE).games:
        directa = play_game(
            jugadores[g.black].create(g.black_seed), jugadores[g.white].create(g.white_seed)
        )
        assert g.result == directa


def test_el_mismo_numero_da_el_mismo_torneo():
    jugadores = registro(RandomPlayer, GreedyPlayer)
    a = run_tournament(jugadores, seed=42, rounds=2, time_limit=LIMITE)
    b = run_tournament(jugadores, seed=42, rounds=2, time_limit=LIMITE)
    assert sin_hora(a) == sin_hora(b)


def test_otro_numero_da_otras_partidas():
    jugadores = registro(RandomPlayer, GreedyPlayer)
    a = run_tournament(jugadores, seed=1, rounds=2, time_limit=LIMITE)
    b = run_tournament(jugadores, seed=2, rounds=2, time_limit=LIMITE)
    assert [g.result.moves for g in a.games] != [g.result.moves for g in b.games]


def test_un_bot_nuevo_no_cambia_las_partidas_de_los_demas():
    antes = run_tournament(registro(RandomPlayer, GreedyPlayer), rounds=2, time_limit=LIMITE)
    despues = run_tournament(
        registro(RandomPlayer, GreedyPlayer, CambiaDeNombre), rounds=2, time_limit=LIMITE
    )
    viejos = {"aleatorio", "avaricioso"}
    comunes = [g.to_dict() for g in despues.games if {g.black, g.white} <= viejos]
    assert comunes == [g.to_dict() for g in antes.games]


def test_el_torneo_no_imprime_nada():
    salida = io.StringIO()
    with redirect_stdout(salida):
        run_tournament(registro(RandomPlayer, GreedyPlayer), rounds=1, time_limit=LIMITE)
    assert salida.getvalue() == ""


def test_parametros_no_validos():
    with pytest.raises(ValueError):
        run_tournament(registro(RandomPlayer), rounds=0)
    with pytest.raises(ValueError):
        run_tournament(registro(RandomPlayer), time_limit=0)


# -- 5.2 Sobrevivir a un jugador malo -------------------------------------- #


def comprobar_que_solo_pierde_el_roto(roto: type[Player], motivo: str) -> None:
    """El roto pierde todas sus partidas con motivo; las de los demás entre sí no se tocan."""
    resultado = run_tournament(registro(RandomPlayer, GreedyPlayer, roto), time_limit=LIMITE)
    nombre = roto.get_name()
    malo = puesto(resultado, nombre)
    assert resultado.standings[-1].name == nombre  # queda último
    assert malo.wins == malo.draws == 0
    assert malo.forfeits == malo.losses == malo.played == 2 * 2 * resultado.rounds
    assert all(motivo in m for m in malo.forfeit_reasons), malo.forfeit_reasons
    for g in resultado.games:
        if nombre in (g.black, g.white):
            assert g.winner_name != nombre and g.result.forfeit is not None
        else:
            assert g.result.forfeit is None
    # La tabla completa se produce igual, con el motivo debajo.
    tabla = format_table(resultado)
    assert all(s.name in tabla for s in resultado.standings)
    assert motivo in tabla


def test_un_bot_que_falla_queda_ultimo_con_el_motivo_registrado():
    comprobar_que_solo_pierde_el_roto(LanzaExcepcion, "RuntimeError: fallo en choose_move")


def test_un_bot_que_hace_trampas_pierde_solo_sus_partidas():
    comprobar_que_solo_pierde_el_roto(ModificaElTablero, "TypeError")


def test_un_bot_que_modifica_el_estado_a_escondidas_pierde():
    comprobar_que_solo_pierde_el_roto(ModificaAEscondidas, "modificó el estado")


def test_un_bot_que_se_cuelga_pierde_por_tiempo_y_el_torneo_termina():
    comprobar_que_solo_pierde_el_roto(SeCuelga, "TimeoutError: no respondió en 0.2 s")


def test_un_bot_que_intenta_cerrar_el_programa_no_cierra_el_torneo():
    comprobar_que_solo_pierde_el_roto(SaleDelPrograma, "SystemExit")


def test_un_bot_que_cambia_de_nombre_pierde(monkeypatch):
    jugadores = registro(RandomPlayer, CambiaDeNombre)  # se registra como "cambiadenombre"
    monkeypatch.setattr(CambiaDeNombre, "NOMBRE", "avaricioso")  # y luego dice ser otro
    resultado = run_tournament(jugadores, rounds=1, time_limit=LIMITE)
    malo = puesto(resultado, "cambiadenombre")
    assert malo.forfeits == 2
    assert all("cambió su nombre a 'avaricioso'" in m for m in malo.forfeit_reasons)
    assert {s.name for s in resultado.standings} == {"aleatorio", "cambiadenombre"}


def test_un_bot_que_no_se_puede_crear_pierde_sin_jugar():
    class NoArranca(CambiaDeNombre):
        NOMBRE = "noarranca"

        @classmethod
        def create(cls, seed: int) -> Player:
            raise ValueError("falta un archivo")

    resultado = run_tournament(registro(RandomPlayer, NoArranca), rounds=1, time_limit=LIMITE)
    malo = puesto(resultado, "noarranca")
    assert malo.forfeits == 2
    assert all("no se pudo crear: ValueError: falta un archivo" in m for m in malo.forfeit_reasons)
    assert all(g.result.moves == () for g in resultado.games)


def test_si_infringen_los_dos_pierden_los_dos():
    otro = type("OtroQueFalla", (LanzaExcepcion,), {})
    resultado = run_tournament(registro(LanzaExcepcion, otro), rounds=1, time_limit=LIMITE)
    # play_game da la partida al rival del primero que falla: aquí siempre empiezan las negras.
    assert all(s.forfeits == 1 and s.wins == 1 for s in resultado.standings)


def test_la_capa_de_proteccion_deja_pasar_a_un_bot_correcto():
    class Primero:
        def choose_move(self, state: GameState) -> Move:
            return legal_moves(state)[0]

    protegido = GuardedPlayer(Primero(), LIMITE)  # type: ignore[arg-type]
    resultado = play_game(protegido, GuardedPlayer(Primero(), LIMITE))  # type: ignore[arg-type]
    assert resultado.forfeit is None
    assert resultado == play_game(Primero(), Primero())


# -- 5.3 La clasificación en un archivo ------------------------------------ #


def test_el_leaderboard_tiene_version_hora_clasificacion_y_metadatos(tmp_path):
    resultado = run_tournament(registro(RandomPlayer, GreedyPlayer), rounds=1, time_limit=LIMITE)
    ruta = write_leaderboard(resultado, tmp_path / "results" / "leaderboard.json")
    datos = json.loads(ruta.read_text(encoding="utf-8"))

    assert datos["schema_version"] == SCHEMA_VERSION
    assert datetime.fromisoformat(datos["finished_at"]).tzinfo is not None
    assert [s["rank"] for s in datos["standings"]] == [1, 2]
    primero = datos["standings"][0]
    assert primero["name"] == "avaricioso"
    assert primero["icon"] == "😈"  # se guarda en UTF-8, no como \ud83d...
    for clave in ("authors", "description", "played", "wins", "draws", "losses", "points"):
        assert clave in primero
    assert len(datos["games"]) == 2


def test_las_jugadas_del_leaderboard_reproducen_la_partida(tmp_path):
    resultado = run_tournament(registro(RandomPlayer, GreedyPlayer), rounds=1, time_limit=LIMITE)
    datos = json.loads(write_leaderboard(resultado, tmp_path / "l.json").read_text("utf-8"))
    for guardada, original in zip(datos["games"], resultado.games, strict=True):
        assert tuple(str_to_move(j) for j in guardada["moves"]) == original.result.moves


def test_el_comando_regenera_el_archivo_desde_cero(tmp_path, capsys):
    ruta = tmp_path / "nueva" / "leaderboard.json"
    assert main(["--rondas", "1", "--salida", str(ruta)]) == 0
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert {s["name"] for s in datos["standings"]} >= {"aleatorio", "avaricioso"}
    salida = capsys.readouterr().out
    assert "avaricioso" in salida and "Clasificación guardada en" in salida
    assert not (tmp_path / "nueva" / "leaderboard.json.tmp").exists()
