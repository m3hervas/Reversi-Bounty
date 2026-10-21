"""Tests del módulo que juega una partida completa en la terminal."""

from __future__ import annotations

import random

import pytest

from reversibounty import (
    GameState,
    apply_move,
    initial_state,
    is_terminal,
    legal_moves,
    move_to_str,
    score,
    terminal,
)


def partida_al_azar(semilla: int) -> tuple[list[str], GameState]:
    """Una partida completa con el motor: devuelve las jugadas escritas y el estado final."""
    rng = random.Random(semilla)
    state = initial_state()
    jugadas: list[str] = []
    while not is_terminal(state):
        jugada = rng.choice(legal_moves(state))
        jugadas.append(move_to_str(jugada))
        state = apply_move(state, jugada)
    return jugadas, state


def jugar_con(entradas: list[str]) -> tuple[GameState, str]:
    """Ejecuta el bucle con entradas ya escritas y devuelve estado final y texto mostrado."""
    cola = iter(entradas)
    salida: list[str] = []

    def leer(_: str) -> str:
        try:
            return next(cola)
        except StopIteration:
            raise EOFError from None

    estado = terminal.jugar(leer=leer, escribir=salida.append, color=False)
    return estado, "\n".join(salida)


@pytest.mark.parametrize("semilla", [0, 1, 2])
def test_partida_completa_llega_al_final_y_anuncia_resultado(semilla):
    jugadas, esperado = partida_al_azar(semilla)
    estado, texto = jugar_con(jugadas)
    assert is_terminal(estado)
    assert score(estado) == score(esperado)
    assert "Fin de la partida" in texto
    assert "Ganan las" in texto or "Empate" in texto


def test_se_avisa_cuando_alguien_pasa():
    for semilla in range(60):
        jugadas, _ = partida_al_azar(semilla)
        _, texto = jugar_con(jugadas)
        if "no pueden mover y pasan" in texto:
            return
    pytest.fail("en 60 partidas al azar no se encontró ningún paso de turno")


def test_jugada_ilegal_se_rechaza_y_se_vuelve_a_preguntar():
    estado, texto = jugar_con(["a1", "q"])
    assert "no es una jugada legal" in texto
    assert score(estado) == (2, 2)


def test_texto_que_no_es_casilla_se_rechaza():
    estado, texto = jugar_con(["hola", "z9", "q"])
    assert texto.count("no es una casilla") == 2
    assert score(estado) == (2, 2)


def test_q_abandona_la_partida():
    estado, texto = jugar_con(["d3", "q"])
    assert "Partida abandonada" in texto
    assert not is_terminal(estado)


def test_cerrar_la_entrada_abandona_sin_romperse():
    estado, texto = jugar_con([])
    assert "Partida abandonada" in texto
    assert score(estado) == (2, 2)


def test_al_empezar_hay_un_inicio_breve():
    _, texto = jugar_con(["q"])
    assert "por ejemplo d3" in texto
    assert "? ayuda completa" in texto
    assert "CÓMO SE JUEGA" not in texto  # la ayuda larga solo sale con "?"


def test_el_comando_ayuda_muestra_las_instrucciones_completas():
    _, texto = jugar_con(["?", "q"])
    assert texto.count("CÓMO SE JUEGA") == 1


def test_se_cuentan_las_fichas_volteadas():
    _, texto = jugar_con(["d3", "q"])
    assert "juegan d3 y voltean 1 ficha." in texto


def test_tablero_sin_color_marca_jugadas_y_ultima_jugada():
    estado = initial_state()
    plano = terminal.dibujar_tablero(estado, color=False)
    assert plano.count("+") == 4  # d3, c4, f5, e6
    despues = apply_move(estado, (2, 3))
    plano = terminal.dibujar_tablero(despues, ultima=(2, 3), color=False)
    assert "[X]" in plano
    assert "\x1b[" not in plano


def test_tablero_con_color_usa_codigos_ansi():
    assert "\x1b[" in terminal.dibujar_tablero(initial_state(), color=True)


def test_importar_la_libreria_es_silencioso():
    """El paquete no debe imprimir nada al importarse (solo los comandos lo hacen)."""
    import subprocess
    import sys

    resultado = subprocess.run(
        [sys.executable, "-c", "import reversibounty, reversibounty.terminal"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert resultado.stdout == ""
    assert resultado.stderr == ""


@pytest.mark.parametrize("nombre", ["main_texto", "main_color"])
def test_los_comandos_de_consola_existen(nombre):
    assert callable(getattr(terminal, nombre))


def test_main_texto_juega_y_sale_con_q(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _="": "q")
    assert terminal.main_texto() == 0
    salida = capsys.readouterr().out
    assert "? ayuda completa" in salida
    assert "\x1b[" not in salida  # sin color


def test_main_color_juega_con_color(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _="": "q")
    monkeypatch.setattr(terminal, "_preparar_consola", lambda: None)
    assert terminal.main_color() == 0
    assert "\x1b[" in capsys.readouterr().out
