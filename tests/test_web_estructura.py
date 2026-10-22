"""La estructura de la web: apartados, rutas, enlaces y archivos tienen que cuadrar entre sí.

Una web estática sin servidor no avisa de un enlace roto ni de un apartado sin ruta: se queda
en blanco. Estos tests lo comprueban sin navegador, leyendo los archivos.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parent.parent / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "js" / "app.js").read_text(encoding="utf-8")


class Lector(HTMLParser):
    """Recoge lo que hace falta del HTML: ids, secciones, enlaces y archivos."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.vistas: list[str] = []
        self.rutas_de_nav: list[str] = []
        self.hashes: list[str] = []
        self.scroll: list[str] = []
        self.archivos: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "section" and "data-view" in a:
            self.vistas.append(a["data-view"])
        if tag == "a" and "data-route" in a:
            self.rutas_de_nav.append(a["data-route"])
        if tag == "a" and a.get("href", "").startswith("#/"):
            self.hashes.append(a["href"])
        if "data-scroll" in a:
            self.scroll.append(a["data-scroll"])
        for clave in ("src", "href"):
            valor = a.get(clave, "")
            if valor and not re.match(r"^(https?:|#|data:|mailto:)", valor) and tag in ("script", "link"):
                self.archivos.append(valor.split("?")[0])


lector = Lector()
lector.feed(HTML)
RUTAS = set(re.findall(r'(?:^|\s)"?([a-z]*)"?\s*:\s*\{\s*view:\s*"([a-z]+)"', APP))


def test_hay_un_apartado_por_cada_ruta_y_al_reves():
    vistas_de_rutas = {vista for _, vista in RUTAS}
    assert vistas_de_rutas == set(lector.vistas)


def test_cada_apartado_tiene_su_enlace_en_la_navegacion_o_es_la_portada():
    assert set(lector.rutas_de_nav) == set(lector.vistas) - {"inicio"}


def test_los_enlaces_internos_llevan_a_apartados_que_existen():
    nombres = {nombre for nombre, _ in RUTAS}
    for enlace in lector.hashes:
        destino = enlace.removeprefix("#/")
        assert destino in nombres, f"el enlace {enlace} no lleva a ningún apartado"


def test_el_script_de_la_cabecera_conoce_todos_los_apartados():
    # Evita el parpadeo: el <head> fija la vista antes de pintar, así que debe saber los nombres.
    cabecera = HTML.split("</script>")[0]
    for vista in set(lector.vistas) - {"inicio"}:
        assert f'"{vista}"' in cabecera, f"el script del <head> no conoce «{vista}»"


def test_las_reglas_de_css_muestran_cada_apartado():
    base = (WEB / "css" / "base.css").read_text(encoding="utf-8")
    for vista in lector.vistas:
        assert f'html[data-view="{vista}"] .view[data-view="{vista}"]' in base, vista


def test_los_botones_del_indice_llevan_a_secciones_que_existen():
    for destino in lector.scroll:
        assert destino in lector.ids, f"el índice apunta a #{destino}, que no existe"


def test_no_hay_identificadores_repetidos():
    repetidos = {i for i in lector.ids if lector.ids.count(i) > 1}
    assert not repetidos, repetidos


@pytest.mark.parametrize("archivo", sorted(set(lector.archivos)))
def test_cada_archivo_que_carga_la_pagina_existe(archivo):
    assert (WEB / archivo).is_file(), f"index.html carga {archivo}, que no existe"


def test_cada_modulo_de_js_registra_su_vista():
    for vista in ("jugar", "reglas", "bots"):
        assert vista in lector.vistas
        fuentes = "".join(p.read_text(encoding="utf-8") for p in (WEB / "js").glob("*.js"))
        assert re.search(rf"RB\.views\.{vista}\s*=", fuentes), f"ningún .js define RB.views.{vista}"


def test_ninguna_ruta_es_absoluta_para_que_funcione_en_github_pages():
    """GitHub Pages sirve la web bajo /Reversi-Bounty/: una ruta que empiece por / se rompe."""
    for fichero in [WEB / "index.html", *(WEB / "js").glob("*.js"), *(WEB / "css").glob("*.css")]:
        texto = fichero.read_text(encoding="utf-8")
        for coincidencia in re.finditer(r"""(?:src|href|url\()\s*=?\s*["']?(/[a-zA-Z][^"')\s]*)""", texto):
            pytest.fail(f"{fichero.name} usa la ruta absoluta {coincidencia.group(1)}")


def test_las_paginas_nuevas_no_inyectan_html_con_datos_ajenos():
    for nombre in ("bots.js", "reglas.js"):
        texto = (WEB / "js" / nombre).read_text(encoding="utf-8")
        assert "innerHTML" not in texto, f"{nombre} usa innerHTML"
        assert "insertAdjacentHTML" not in texto, f"{nombre} usa insertAdjacentHTML"
