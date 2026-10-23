"""Tests de ``scripts/build_web.py``: el zip que descarga la web tiene todo lo que necesita.

La prueba de verdad es importar el contenido del zip **en un Python aparte**, como hace
Pyodide en el navegador: descomprimirlo, ponerlo al principio de ``sys.path`` y cargar el
registro desde dentro. Si falta algo, falla aquí y no en la página publicada.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def build_web():
    """El script como módulo (``scripts/`` no es un paquete, se carga por su ruta)."""
    spec = importlib.util.spec_from_file_location("build_web", RAIZ / "scripts" / "build_web.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def zip_web(build_web, tmp_path):
    return build_web.build(tmp_path / "py.zip")


def test_el_zip_contiene_el_paquete_el_registro_y_el_puente(zip_web):
    nombres = set(zipfile.ZipFile(zip_web).namelist())
    assert "webglue.py" in nombres
    for modulo in ("__init__", "game", "player", "match", "manifest", "bots/random_player"):
        assert f"reversibounty/{modulo}.py" in nombres
    assert "players/builtin/players.yaml" in nombres
    assert "players/custom/players.yaml" in nombres


def test_el_zip_tiene_todos_los_archivos_del_paquete(zip_web):
    nombres = set(zipfile.ZipFile(zip_web).namelist())
    paquete = RAIZ / "src" / "reversibounty"
    for ruta in paquete.rglob("*.py"):
        assert ruta.relative_to(paquete.parent).as_posix() in nombres


def test_el_zip_no_lleva_caches_ni_bytecode(zip_web):
    for nombre in zipfile.ZipFile(zip_web).namelist():
        assert "__pycache__" not in nombre and not nombre.endswith(".pyc")


def test_el_zip_es_reproducible(build_web, tmp_path):
    uno = build_web.build(tmp_path / "uno.zip").read_bytes()
    dos = build_web.build(tmp_path / "dos.zip").read_bytes()
    assert uno == dos


def test_main_crea_el_zip_donde_se_le_pide(build_web, tmp_path, capsys):
    destino = tmp_path / "sub" / "py.zip"
    assert build_web.main(["--out", str(destino)]) == 0
    assert destino.is_file()
    assert "py.zip" in capsys.readouterr().out


def test_lo_descomprimido_se_importa_en_un_python_limpio(zip_web, tmp_path):
    """Como en el navegador: descomprimir, ponerlo primero en sys.path e importar.

    Se ejecuta en un proceso aparte y aislado (``-I``) para que no valga el paquete
    instalado en el entorno de desarrollo: ``reversibounty`` tiene que salir del zip.
    """
    carpeta = tmp_path / "lib"
    zipfile.ZipFile(zip_web).extractall(carpeta)
    codigo = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(carpeta)!r})\n"
        "import reversibounty, webglue\n"
        f"respuesta = json.loads(webglue.init(json.dumps({str(carpeta / 'players')!r})))\n"
        "print(json.dumps({'paquete': reversibounty.__file__, 'respuesta': respuesta}))\n"
    )
    salida = subprocess.run(
        [sys.executable, "-I", "-c", codigo], capture_output=True, text=True, check=True
    )
    datos = json.loads(salida.stdout)
    assert Path(datos["paquete"]).resolve().is_relative_to(carpeta.resolve())
    assert datos["respuesta"]["ok"], datos["respuesta"]
    assert "Aleatorio" in [j["name"] for j in datos["respuesta"]["result"]]


def test_tambien_se_importa_directamente_desde_el_zip(zip_web):
    """El paquete y el puente se pueden importar sin descomprimir (zipimport)."""
    codigo = (
        "import sys\n"
        f"sys.path.insert(0, {str(zip_web)!r})\n"
        "import reversibounty.game, webglue\n"
        "print(reversibounty.game.__file__)\n"
    )
    salida = subprocess.run(
        [sys.executable, "-I", "-c", codigo], capture_output=True, text=True, check=True
    )
    assert "py.zip" in salida.stdout
