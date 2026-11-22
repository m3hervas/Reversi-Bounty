"""Cada personaje juega con su propio dibujo en las fichas (web/img/fichas y play.css)."""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
CREW = (WEB / "js" / "crew.js").read_text(encoding="utf-8")
CSS = (WEB / "css" / "play.css").read_text(encoding="utf-8")
FICHAS = re.findall(r'ficha:\s*"([a-z0-9]+)"', CREW)


def test_cada_personaje_tiene_su_ficha():
    assert set(FICHAS) == {"buggy", "wapol", "zeff", "nami", "kraken", "karoo", "mr5", "brook"}
    assert len(FICHAS) == len(set(FICHAS))  # dos personajes no comparten dibujo


def test_cada_ficha_tiene_su_dibujo_en_los_dos_bandos():
    for ficha in FICHAS:
        assert (WEB / "img" / "fichas" / f"{ficha}.svg").is_file()
        for bando in ("sombreros", "calaveras"):
            assert f'.play[data-ficha-{bando}="{ficha}"]' in CSS


def test_los_dibujos_son_svg_sin_scripts():
    for svg in (WEB / "img" / "fichas").glob("*.svg"):
        texto = svg.read_text(encoding="utf-8")
        assert texto.lstrip().startswith("<svg")
        assert "<script" not in texto and "href" not in texto
