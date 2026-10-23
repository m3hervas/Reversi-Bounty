"""La página «Añade tu bot» no puede enseñar nada que no funcione.

Igual que el tutorial, el código de la página se saca del HTML y se ejecuta de verdad: el bot de
ejemplo se instala en una carpeta de prueba, se registra con la línea del YAML que enseña la
página, se carga con el registro real y pasa la prueba de contrato y el estilo (ruff). Y la tabla
de métodos coincide con los métodos abstractos de ``Player``.
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from contrato import verificar_contrato
from reversibounty import Player
from reversibounty.manifest import load_players

RAIZ = Path(__file__).resolve().parent.parent
HTML = (RAIZ / "web" / "index.html").read_text(encoding="utf-8")
PAGINA = HTML[HTML.index('data-view="anadir"'):]


def codigo(ident: str) -> str:
    """El texto del bloque de código de la página con ese identificador."""
    patron = rf'data-code="{ident}">.*?<pre><code>(.*?)</code></pre>'
    encontrado = re.search(patron, PAGINA, re.DOTALL)
    assert encontrado, f"la página no tiene el bloque de código «{ident}»"
    return html.unescape(encontrado.group(1))


@pytest.fixture
def players_dir(tmp_path: Path) -> Path:
    """Una carpeta ``players/`` donde se ha seguido la página al pie de la letra."""
    custom = tmp_path / "players" / "custom"
    custom.mkdir(parents=True)
    (custom / "mi_bot.py").write_text(codigo("bot"), encoding="utf-8")
    (custom / "players.yaml").write_text(codigo("registro"), encoding="utf-8")
    return tmp_path / "players"


def test_el_bot_de_ejemplo_se_registra_con_la_linea_que_ensena_la_pagina(players_dir):
    players = load_players(players_dir)
    assert list(players) == ["Mi bot"]
    assert issubclass(players["Mi bot"], Player)
    assert players["Mi bot"].get_icon() == "🎲"


def test_el_bot_de_ejemplo_cumple_el_contrato(players_dir):
    verificar_contrato(load_players(players_dir)["Mi bot"])


def test_el_bot_de_ejemplo_pasa_el_estilo_del_proyecto(players_dir):
    resultado = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--config", str(RAIZ / "pyproject.toml"), str(players_dir)],
        capture_output=True, text=True, check=False,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_el_registro_de_la_pagina_es_yaml_valido_con_archivo_y_clase():
    datos = yaml.safe_load(codigo("registro"))
    assert datos == {"players": [{"file": "mi_bot.py", "class": "MiBot"}]}


def test_los_cinco_metodos_de_la_pagina_son_los_abstractos_de_player():
    bloque = re.search(r'<h2 class="h3">Los cinco métodos</h2>(.*?)</dl>', PAGINA, re.DOTALL)
    assert bloque
    en_pagina = set(re.findall(r"<dt><code>(\w+)\(", bloque.group(1)))
    assert en_pagina == set(Player.__abstractmethods__)


def test_los_nombres_de_los_bots_de_la_pagina_empiezan_por_mayuscula():
    nombre = re.search(r'return "([^"]+)"', codigo("bot")).group(1)
    assert nombre[:1].isupper()


def test_los_comandos_de_la_pagina_existen_en_el_tutorial():
    """Las mismas comprobaciones que manda ejecutar el tutorial, sin inventar ninguna."""
    tutorial = (RAIZ / "docs" / "tutorial.md").read_text(encoding="utf-8")
    for orden in ("pytest tests/test_contract.py -v", "pytest -q", "ruff check .", 'pip install -e ".[dev]"'):
        assert orden in codigo("comprobar") + codigo("preparar")
        assert orden in tutorial, orden


def test_la_ruta_esta_en_la_navegacion_en_el_javascript_y_en_el_arranque():
    app = (RAIZ / "web" / "js" / "app.js").read_text(encoding="utf-8")
    assert 'anadir: { view: "anadir"' in app
    assert 'data-route="anadir"' in HTML
    assert '"anadir"]' in HTML  # el aviso de la cabecera que fija la vista antes de pintar
    assert "js/anadir.js" in HTML


# -- La estructura de la página ------------------------------------------------ #


def test_el_ejemplo_va_a_la_izquierda_y_la_guia_a_la_derecha_bajo_el_titulo():
    titulo = PAGINA.index('id="t-anadir"')
    ejemplo = PAGINA.index('class="intro__code"')
    guia = PAGINA.index('class="intro__how"')
    assert titulo < ejemplo < guia
    assert 'data-code="bot"' in PAGINA[ejemplo:guia]


def test_el_titulo_no_tiene_descripcion():
    cabecera = PAGINA[PAGINA.index("<header"):PAGINA.index("</header>")]
    assert 'class="lede"' not in cabecera
    assert "<p>" not in cabecera


def test_los_metodos_y_lo_que_recibe_son_dos_bloques_de_la_misma_fila():
    duo = PAGINA[PAGINA.index('class="duo"'):]
    duo = duo[:duo.index("</section>")]
    assert duo.count('class="duo__col"') == 2
    assert "Los cinco métodos" in duo and "Qué recibe tu bot" in duo


def test_la_guia_del_pull_request_ya_no_esta_y_el_envio_va_al_final():
    assert 'id="a-pr"' not in PAGINA
    assert "El pull request</h2>" not in PAGINA
    assert PAGINA.index('id="a-enviar"') > PAGINA.index('id="a-fallos"') > PAGINA.index('id="a-reglas"')
    # Solo lo que va después del envío es la llamada final.
    assert 'id="a-enviar"' in PAGINA and PAGINA.index('id="a-enviar"') < PAGINA.index("h-cta-anadir")
