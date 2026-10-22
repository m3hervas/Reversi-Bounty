"""El registro de jugadores: qué bots están admitidos en el proyecto.

Los jugadores se descubren a partir de **listas editadas a mano**, nunca escaneando una
carpeta. Es una decisión deliberada: cuando alguien abre un pull request para añadir un
bot, quien lo revisa ve en un mismo diff el archivo nuevo y la única línea que lo admite.
Esa revisión es la puerta de seguridad. Escanear la carpeta ocultaría qué se está
admitiendo y ejecutaría el código de un desconocido solo para descubrirlo.

Hay dos listas, cada una junto a los jugadores que admite::

    players/
      builtin/players.yaml   los jugadores de referencia que trae el proyecto
      custom/players.yaml    los enviados por pull request

Separarlas mantiene el diff de un envío dentro de ``custom/``: dos envíos no chocan en la
misma lista y ninguno puede tocar a los de referencia.

Cada entrada dice **dónde está** la clase y **cuál es**, y nada más::

    players:
      - module: reversibounty.bots.random_player   # una clase del propio paquete
        class: RandomPlayer
      - file: mi_bot.py                            # un archivo junto a la lista
        class: MiBot

El nombre, los autores, la descripción y el emoji NO se repiten aquí: los declara la propia
clase (``get_name`` y compañía). Así hay una única fuente de verdad y no pueden desviarse.
La lista responde a "¿está admitido?" y la clase a "¿qué es?".

Cargar un jugador **importa su archivo**, y eso ejecuta el código de ese archivo. Es seguro
solo porque los archivos llegan por pull requests revisados.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from .player import Player

# Un emoji o una secuencia de emojis que se ve como uno solo: con variante (U+FE0F), con tono
# de piel, unidos con U+200D (como la bandera pirata), una bandera de país o un número con
# marco. Es una aproximación sin librerías externas: cubre los bloques de emojis habituales.
_EMOJI = "[\U0001f000-\U0001faff←-⇿⌚-⏿☀-➿⬀-⯿]"
_UNIDAD = f"{_EMOJI}️?[\U0001f3fb-\U0001f3ff]?"
_UN_EMOJI = re.compile(
    rf"(?:{_UNIDAD}(?:‍{_UNIDAD})*|[\U0001f1e6-\U0001f1ff]{{2}}|[0-9#*]️?⃣)"
)

_CLAVES_DE_ENTRADA = {"file", "module", "class"}


class ManifestError(Exception):
    """Una lista de jugadores mal escrita o un jugador que no cumple el contrato."""


def is_single_emoji(text: object) -> bool:
    """Indica si ``text`` es exactamente un emoji (y nada más).

    Args:
        text: lo que se quiere comprobar; cualquier objeto.

    Returns:
        ``True`` si es un único emoji, aunque esté formado por varios caracteres
        Unicode (como la bandera pirata). ``False`` para texto, espacios sobrantes o
        varios emojis.
    """
    return isinstance(text, str) and _UN_EMOJI.fullmatch(text) is not None


def default_players_dir() -> Path:
    """La carpeta ``players/`` del repositorio (solo existe al trabajar desde el código)."""
    return Path(__file__).resolve().parents[2] / "players"


def check_identity(cls: type[Player]) -> None:
    """Comprueba que la identidad que declara una clase es válida.

    Args:
        cls: la clase del jugador.

    Raises:
        ManifestError: si el nombre, los autores, la descripción o el emoji no son válidos.
    """
    etiqueta = cls.__name__
    name = cls.get_name()
    if not isinstance(name, str) or not name.strip() or name != name.strip():
        raise ManifestError(
            f"{etiqueta}: get_name() debe devolver un texto no vacío sin espacios sobrantes"
        )
    authors = cls.get_authors()
    if (
        not isinstance(authors, list)
        or not authors
        or not all(isinstance(a, str) and a.strip() for a in authors)
    ):
        raise ManifestError(
            f"{etiqueta}: get_authors() debe devolver una lista de textos no vacía"
        )
    description = cls.get_description()
    if not isinstance(description, str) or not description.strip():
        raise ManifestError(f"{etiqueta}: get_description() debe devolver un texto no vacío")
    icon = cls.get_icon()
    if not is_single_emoji(icon):
        raise ManifestError(f"{etiqueta}: get_icon() debe devolver un único emoji, no {icon!r}")


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    """Lee una lista de jugadores y comprueba su forma, sin cargar ningún jugador."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ManifestError(f"{path}: no es un YAML válido: {error}") from error
    if data is None:
        return []
    if not isinstance(data, dict) or set(data) != {"players"}:
        raise ManifestError(f"{path}: debe contener solo la clave 'players'")
    entries = data["players"]
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise ManifestError(f"{path}: 'players' debe ser una lista")
    for number, entry in enumerate(entries, start=1):
        _check_entry(path, number, entry)
    return entries


def _check_entry(path: Path, number: int, entry: object) -> None:
    donde = f"{path}, entrada {number}"
    if not isinstance(entry, dict):
        raise ManifestError(f"{donde}: debe ser un diccionario con 'file' o 'module', y 'class'")
    unknown = set(entry) - _CLAVES_DE_ENTRADA
    if unknown:
        raise ManifestError(f"{donde}: claves desconocidas: {', '.join(sorted(map(str, unknown)))}")
    if ("file" in entry) == ("module" in entry):
        raise ManifestError(f"{donde}: indica exactamente una de 'file' o 'module'")
    if not isinstance(entry.get("class"), str) or not entry["class"]:
        raise ManifestError(f"{donde}: falta 'class'")
    for key in ("file", "module"):
        if key in entry and (not isinstance(entry[key], str) or not entry[key]):
            raise ManifestError(f"{donde}: '{key}' debe ser un texto no vacío")


def _load_module(entry: dict[str, Any], manifest: Path) -> Any:
    """Importa el módulo o el archivo que indica una entrada."""
    if "module" in entry:
        try:
            return importlib.import_module(entry["module"])
        except ImportError as error:
            raise ManifestError(
                f"{manifest}: no se puede importar {entry['module']!r}: {error}"
            ) from error
    path = manifest.parent / entry["file"]
    if not path.is_file():
        raise ManifestError(f"{manifest}: no existe el archivo {path}")
    name = f"_reversibounty_player_{manifest.parent.name}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ManifestError(f"{manifest}: no se puede cargar {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise ManifestError(f"{manifest}: {path.name} falla al importarse: {error!r}") from error
    return module


def _load_class(entry: dict[str, Any], manifest: Path) -> type[Player]:
    module = _load_module(entry, manifest)
    cls = getattr(module, entry["class"], None)
    if cls is None:
        raise ManifestError(f"{manifest}: no existe la clase {entry['class']!r}")
    if not (isinstance(cls, type) and issubclass(cls, Player)) or cls is Player:
        raise ManifestError(f"{manifest}: {entry['class']} no es una subclase de Player")
    # Primero se intenta crear: si la clase está incompleta, Python dice qué método falta.
    try:
        jugador = cls.create(seed=0)
    except TypeError as error:  # una clase abstracta que no implementa algún método
        raise ManifestError(f"{manifest}: {entry['class']} no se puede crear: {error}") from error
    except Exception as error:
        raise ManifestError(
            f"{manifest}: {entry['class']}.create(seed=0) falla: {error!r}"
        ) from error
    if not isinstance(jugador, Player):
        raise ManifestError(f"{manifest}: {entry['class']}.create() debe devolver un Player")
    check_identity(cls)
    return cls


def load_players(players_dir: str | Path | None = None) -> dict[str, type[Player]]:
    """Carga todos los jugadores admitidos, primero los de referencia y luego los enviados.

    Para cada entrada importa la clase y comprueba que es una subclase de ``Player``, que su
    identidad es válida y que se puede crear con ``create(seed=0)``.

    Args:
        players_dir: la carpeta con ``builtin/players.yaml`` y ``custom/players.yaml``. Por
            defecto, la carpeta ``players/`` del repositorio. Basta con que exista una de las
            dos listas.

    Returns:
        Un diccionario ``nombre -> clase`` en orden de admisión.

    Raises:
        ManifestError: si no hay ninguna lista, si una está mal escrita, si un jugador no se
            puede cargar o no cumple el contrato, o si dos jugadores tienen el mismo nombre.
    """
    base = Path(players_dir) if players_dir is not None else default_players_dir()
    manifests = [base / carpeta / "players.yaml" for carpeta in ("builtin", "custom")]
    existentes = [m for m in manifests if m.is_file()]
    if not existentes:
        raise ManifestError(f"no hay ninguna lista de jugadores en {base}")

    players: dict[str, type[Player]] = {}
    origen: dict[str, Path] = {}
    for manifest in existentes:
        for entry in _read_manifest(manifest):
            cls = _load_class(entry, manifest)
            name = cls.get_name()
            if name in players:
                raise ManifestError(
                    f"{manifest}: el nombre {name!r} ya lo usa {players[name].__name__} "
                    f"({origen[name]})"
                )
            players[name] = cls
            origen[name] = manifest
    return players
