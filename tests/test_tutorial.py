"""El ejemplo del tutorial debe funcionar de verdad: quien lo copie no puede encontrarse un error.

El test saca de ``docs/tutorial.md`` el bot y la entrada de la lista, los instala en una carpeta
de prueba, los carga con el registro real y les pasa la prueba de contrato. Si alguien cambia la
API y se olvida del tutorial, este test se pone en rojo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from contrato import verificar_contrato
from reversibounty import Player
from reversibounty.manifest import load_players

TUTORIAL = Path(__file__).resolve().parent.parent / "docs" / "tutorial.md"


def bloque(titulo: str) -> str:
    """El contenido del bloque de código del tutorial que lleva ese título."""
    patron = rf'```(?:python|yaml) title="{re.escape(titulo)}"\n(.*?)```'
    encontrado = re.search(patron, TUTORIAL.read_text(encoding="utf-8"), re.DOTALL)
    assert encontrado, f"el tutorial no tiene un bloque con el título {titulo!r}"
    return encontrado.group(1)


@pytest.fixture
def players_dir(tmp_path: Path) -> Path:
    """Una carpeta ``players/`` donde se ha seguido el tutorial al pie de la letra."""
    custom = tmp_path / "players" / "custom"
    custom.mkdir(parents=True)
    (custom / "esquinero.py").write_text(bloque("players/custom/esquinero.py"), encoding="utf-8")
    (custom / "players.yaml").write_text(bloque("players/custom/players.yaml"), encoding="utf-8")
    return tmp_path / "players"


def test_el_ejemplo_del_tutorial_se_registra(players_dir):
    players = load_players(players_dir)
    assert list(players) == ["esquinero"]
    assert issubclass(players["esquinero"], Player)
    assert players["esquinero"].get_icon() == "📐"


def test_el_ejemplo_del_tutorial_cumple_el_contrato(players_dir):
    verificar_contrato(load_players(players_dir)["esquinero"])


def test_el_ejemplo_toma_una_esquina_cuando_puede():
    from reversibounty import GameState

    codigo = bloque("players/custom/esquinero.py")
    espacio: dict[str, object] = {}
    exec(compile(codigo, "esquinero.py", "exec"), espacio)  # noqa: S102 - es nuestro propio ejemplo
    esquinero = espacio["Esquinero"].create(seed=0)  # type: ignore[attr-defined]
    # Las negras pueden jugar en a1 (esquina) tomando la ficha blanca de b1.
    filas = ["........"] * 8
    filas[0] = ".OX....."
    valores = {"X": 1, "O": -1, ".": 0}
    estado = GameState(tuple(tuple(valores[c] for c in fila) for fila in filas), 1)
    assert esquinero.choose_move(estado) == (0, 0)


def test_las_entradas_de_la_tabla_de_errores_existen_en_el_registro():
    """Los mensajes que el tutorial promete deben existir en el código del registro."""
    fuente = (TUTORIAL.parent.parent / "src" / "reversibounty" / "manifest.py").read_text(
        encoding="utf-8"
    )
    for fragmento in [
        "no existe el archivo",
        "no existe la clase",
        "no es una subclase de Player",
        "no se puede crear",
        "debe devolver un único emoji",
        "ya lo usa",
        "falla al importarse",
    ]:
        assert fragmento in fuente, f"el tutorial menciona {fragmento!r} pero el código no lo dice"
