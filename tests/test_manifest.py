"""Tests del registro de jugadores: lo que admite, y lo que rechaza con un mensaje claro."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from reversibounty import Player
from reversibounty.manifest import ManifestError, check_identity, is_single_emoji, load_players

BOT = '''
from reversibounty import GameState, Move, Player, legal_moves


class {clase}(Player):
    @classmethod
    def get_name(cls) -> str:
        return {nombre!r}

    @classmethod
    def get_authors(cls) -> list[str]:
        return {autores!r}

    @classmethod
    def get_description(cls) -> str:
        return {descripcion!r}

    @classmethod
    def get_icon(cls) -> str:
        return {icono!r}

    def choose_move(self, state: GameState) -> Move:
        return legal_moves(state)[0]
'''


def bot(clase="MiBot", nombre="mi-bot", autores=("Tests",), descripcion="Una descripción.", icono="🎯"):
    return BOT.format(
        clase=clase, nombre=nombre, autores=list(autores), descripcion=descripcion, icono=icono
    )


def montar(tmp_path: Path, custom: str | None = None, builtin: str | None = None, **archivos: str) -> Path:
    """Crea una carpeta ``players/`` de prueba con las listas y los archivos indicados."""
    base = tmp_path / "players"
    for carpeta, contenido in (("builtin", builtin), ("custom", custom)):
        if contenido is not None:
            (base / carpeta).mkdir(parents=True, exist_ok=True)
            (base / carpeta / "players.yaml").write_text(textwrap.dedent(contenido), encoding="utf-8")
    for nombre, texto in archivos.items():
        destino = base / "custom" / f"{nombre}.py"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    return base


def lista(*entradas: str) -> str:
    return "players:\n" + "".join(f"  - {e}\n" for e in entradas)


# -- El registro real del proyecto ----------------------------------------- #


def test_el_registro_real_carga_y_todos_son_player():
    players = load_players()
    assert "Aleatorio" in players
    assert all(issubclass(cls, Player) for cls in players.values())


def test_las_claves_del_registro_son_los_nombres_de_las_clases():
    for nombre, cls in load_players().items():
        assert cls.get_name() == nombre


# -- Cargar jugadores ------------------------------------------------------- #


def test_carga_un_archivo_junto_a_la_lista(tmp_path):
    base = montar(tmp_path, custom=lista("{file: mi_bot.py, class: MiBot}"), mi_bot=bot())
    players = load_players(base)
    assert list(players) == ["mi-bot"]
    assert players["mi-bot"].get_icon() == "🎯"


def test_carga_una_clase_de_un_modulo_importable(tmp_path):
    base = montar(
        tmp_path,
        builtin=lista("{module: reversibounty.bots.random_player, class: RandomPlayer}"),
    )
    assert list(load_players(base)) == ["Aleatorio"]


def test_primero_los_de_referencia_y_luego_los_enviados(tmp_path):
    base = montar(
        tmp_path,
        builtin=lista("{module: reversibounty.bots.random_player, class: RandomPlayer}"),
        custom=lista("{file: mi_bot.py, class: MiBot}"),
        mi_bot=bot(),
    )
    assert list(load_players(base)) == ["Aleatorio", "mi-bot"]


def test_una_lista_vacia_es_valida(tmp_path):
    base = montar(tmp_path, custom="players: []\n", builtin="")
    assert load_players(base) == {}


def test_basta_con_que_exista_una_de_las_dos_listas(tmp_path):
    base = montar(tmp_path, custom=lista("{file: mi_bot.py, class: MiBot}"), mi_bot=bot())
    assert list(load_players(base)) == ["mi-bot"]


def test_sin_ninguna_lista_da_un_error_claro(tmp_path):
    with pytest.raises(ManifestError, match="ninguna lista"):
        load_players(tmp_path)


# -- Errores en la lista ---------------------------------------------------- #


@pytest.mark.parametrize(
    ("contenido", "mensaje"),
    [
        ("players: [", "YAML"),
        ("otra_cosa: 1\n", "solo la clave 'players'"),
        ("players: 3\n", "debe ser una lista"),
        ("players:\n  - 3\n", "diccionario"),
        ("players:\n  - {class: MiBot}\n", "exactamente una"),
        ("players:\n  - {file: a.py, module: b, class: MiBot}\n", "exactamente una"),
        ("players:\n  - {file: mi_bot.py}\n", "falta 'class'"),
        ("players:\n  - {file: mi_bot.py, class: MiBot, extra: 1}\n", "claves desconocidas"),
    ],
)
def test_una_lista_mal_escrita_da_un_error_claro(tmp_path, contenido, mensaje):
    base = montar(tmp_path, custom=contenido, mi_bot=bot())
    with pytest.raises(ManifestError, match=mensaje):
        load_players(base)


# -- Errores al cargar un jugador ------------------------------------------ #


def test_un_archivo_que_no_existe_da_un_error_claro(tmp_path):
    base = montar(tmp_path, custom=lista("{file: no_existe.py, class: MiBot}"))
    with pytest.raises(ManifestError, match="no existe el archivo"):
        load_players(base)


def test_un_modulo_que_no_se_puede_importar_da_un_error_claro(tmp_path):
    base = montar(tmp_path, custom=lista("{module: no.existe.nunca, class: MiBot}"))
    with pytest.raises(ManifestError, match="no se puede importar"):
        load_players(base)


def test_una_clase_que_no_existe_da_un_error_claro(tmp_path):
    base = montar(tmp_path, custom=lista("{file: mi_bot.py, class: Otra}"), mi_bot=bot())
    with pytest.raises(ManifestError, match="no existe la clase"):
        load_players(base)


def test_una_clase_que_no_es_un_player_se_rechaza(tmp_path):
    base = montar(
        tmp_path, custom=lista("{file: mi_bot.py, class: Falso}"), mi_bot="class Falso:\n    pass\n"
    )
    with pytest.raises(ManifestError, match="no es una subclase de Player"):
        load_players(base)


def test_un_archivo_que_falla_al_importarse_da_un_error_claro(tmp_path):
    base = montar(
        tmp_path, custom=lista("{file: mi_bot.py, class: MiBot}"), mi_bot="raise ValueError('roto')\n"
    )
    with pytest.raises(ManifestError, match="falla al importarse"):
        load_players(base)


def test_una_subclase_incompleta_se_rechaza(tmp_path):
    codigo = "from reversibounty import Player\n\n\nclass MiBot(Player):\n    pass\n"
    base = montar(tmp_path, custom=lista("{file: mi_bot.py, class: MiBot}"), mi_bot=codigo)
    with pytest.raises(ManifestError, match="no se puede crear"):
        load_players(base)


def test_si_create_falla_se_rechaza(tmp_path):
    codigo = bot() + "\n    @classmethod\n    def create(cls, seed):\n        raise RuntimeError('no')\n"
    base = montar(tmp_path, custom=lista("{file: mi_bot.py, class: MiBot}"), mi_bot=codigo)
    with pytest.raises(ManifestError, match="create"):
        load_players(base)


def test_dos_jugadores_con_el_mismo_nombre_se_rechazan(tmp_path):
    base = montar(
        tmp_path,
        custom=lista("{file: uno.py, class: Uno}", "{file: dos.py, class: Dos}"),
        uno=bot(clase="Uno", nombre="repetido"),
        dos=bot(clase="Dos", nombre="repetido"),
    )
    with pytest.raises(ManifestError, match="'repetido' ya lo usa"):
        load_players(base)


def test_un_nombre_ya_usado_por_uno_de_referencia_se_rechaza(tmp_path):
    base = montar(
        tmp_path,
        builtin=lista("{module: reversibounty.bots.random_player, class: RandomPlayer}"),
        custom=lista("{file: mi_bot.py, class: MiBot}"),
        mi_bot=bot(nombre="Aleatorio"),
    )
    with pytest.raises(ManifestError, match="'Aleatorio' ya lo usa"):
        load_players(base)


# -- La identidad que declara una clase ------------------------------------ #


@pytest.mark.parametrize(
    ("campos", "mensaje"),
    [
        ({"nombre": ""}, "get_name"),
        ({"nombre": "  "}, "get_name"),
        ({"nombre": " con-espacios "}, "get_name"),
        ({"autores": ()}, "get_authors"),
        ({"autores": ("",)}, "get_authors"),
        ({"descripcion": ""}, "get_description"),
        ({"descripcion": "   "}, "get_description"),
        ({"icono": ""}, "get_icon"),
        ({"icono": "hola"}, "get_icon"),
        ({"icono": "🎲🎲"}, "get_icon"),
        ({"icono": "x"}, "get_icon"),
    ],
)
def test_una_identidad_invalida_se_rechaza(tmp_path, campos, mensaje):
    base = montar(tmp_path, custom=lista("{file: mi_bot.py, class: MiBot}"), mi_bot=bot(**campos))
    with pytest.raises(ManifestError, match=mensaje):
        load_players(base)


def test_check_identity_acepta_una_identidad_valida():
    from reversibounty.bots import RandomPlayer

    check_identity(RandomPlayer)


# -- Qué cuenta como un único emoji ---------------------------------------- #


@pytest.mark.parametrize(
    "emoji",
    ["🃏", "🎲", "🏴‍☠️", "⚓", "❤️", "👨‍👩‍👧", "🇪🇸", "👍🏽", "1️⃣", "🤖"],
)
def test_son_un_unico_emoji(emoji):
    assert is_single_emoji(emoji)


@pytest.mark.parametrize("texto", ["", "a", "hola", "🎲🎲", " 🎲", "🎲 ", "ab🎲", "1", None, 5, ["🎲"]])
def test_no_son_un_unico_emoji(texto):
    assert not is_single_emoji(texto)
