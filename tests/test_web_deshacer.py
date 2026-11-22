"""Deshacer en la Lucha: el botón existe y vuelve a posiciones que dio el motor."""

from __future__ import annotations

from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
PLAY = (WEB / "js" / "play.js").read_text(encoding="utf-8")


def test_hay_boton_de_deshacer_junto_a_nueva_partida():
    assert 'id="undo"' in HTML
    assert HTML.index('id="again"') < HTML.index('id="undo"')
    assert 'aria-keyshortcuts="Control+Z"' in HTML


def test_deshacer_solo_vuelve_a_posiciones_guardadas_del_motor():
    # Las posiciones salen de game.history, que solo se llena con vistas que devolvió el motor.
    assert "game.history.push(view)" in PLAY
    assert "function undo()" in PLAY and "function canUndo()" in PLAY
    # Deshacer corta la respuesta del bot que estuviera en camino.
    cuerpo = PLAY[PLAY.index("function undo()"):]
    assert "++game.token" in cuerpo[:400]


def test_no_se_deshace_una_partida_con_la_recompensa_cobrada():
    assert "game.rewarded = true" in PLAY
    assert "!game.rewarded" in PLAY


def test_entre_dos_bots_se_puede_parar_y_seguir():
    assert 'id="pause"' in HTML
    assert "function togglePause()" in PLAY
    # Parar no corta una jugada a medias: el bot espera antes de pedir la siguiente.
    assert "if (game.paused) {" in PLAY and "game.waiting = color" in PLAY
