# Tutorial: escribe y envía tu bot

Este tutorial te lleva desde cero hasta un bot fusionado en el proyecto. Al final tendrás un
bot propio jugando en Reversi Bounty, y no habrás tenido que tocar el código del juego.

**Qué necesitas:** Python 3.10 o superior, Git y una cuenta de GitHub.

**Cómo funciona, en una frase:** tu bot es un archivo `.py` en `players/custom/` y una línea en
`players/custom/players.yaml`. Se envía por *pull request*, y nada entra en el proyecto sin que
otra persona lo revise y sin que los tests automáticos pasen.

## 1. Prepara el proyecto

Haz un *fork* del repositorio con el botón **Fork** de
[GitHub](https://github.com/m3hervas/Reversi-Bounty) y clona **tu** copia (cambia
`TU-USUARIO` por tu nombre de usuario). Si ya formas parte del equipo, clona directamente el
repositorio original.

```bash
git clone https://github.com/TU-USUARIO/Reversi-Bounty.git
cd Reversi-Bounty
python -m venv .venv
```

Activa el entorno. En Windows:

```bash
.venv\Scripts\activate
```

En Linux o macOS:

```bash
source .venv/bin/activate
```

Instala el proyecto y comprueba que todo funciona antes de tocar nada:

```bash
pip install -e ".[dev]"
pytest -q
```

Deben pasar todos los tests. Si no pasan, el problema no es tuyo: avisa antes de seguir.

## 2. Crea una rama

Nadie escribe directamente en `main`. Cada cambio va en su propia rama:

```bash
git checkout -b bot-esquinero
```

Usa un nombre corto que diga qué añades, sin espacios ni tildes.

## 3. Escribe tu bot

Crea el archivo `players/custom/esquinero.py` con este contenido. Es un ejemplo **completo**:
cópialo tal cual y luego cámbialo por tu idea.

```python title="players/custom/esquinero.py"
"""Esquinero: toma una esquina si puede; si no, juega una casilla legal al azar."""

import random

from reversibounty import GameState, Move, Player, legal_moves

ESQUINAS = {(0, 0), (0, 7), (7, 0), (7, 7)}


class Esquinero(Player):
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    @classmethod
    def get_name(cls) -> str:
        return "esquinero"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Tu Nombre"]

    @classmethod
    def get_description(cls) -> str:
        return "Toma una esquina si puede; si no, elige una casilla legal al azar."

    @classmethod
    def get_icon(cls) -> str:
        return "📐"

    @classmethod
    def create(cls, seed: int) -> "Esquinero":
        return cls(random.Random(seed))

    def choose_move(self, state: GameState) -> Move:
        jugadas = legal_moves(state)
        esquinas = [jugada for jugada in jugadas if jugada in ESQUINAS]
        return self._rng.choice(esquinas or jugadas)
```

### Qué tienes que implementar

Un bot es una subclase de `Player`. Hay cinco cosas obligatorias:

| Método | Qué devuelve |
|---|---|
| `get_name()` | Un nombre **único** entre todos los jugadores. Se ve en la clasificación. |
| `get_authors()` | Una lista no vacía con los autores. |
| `get_description()` | Una frase que describa la estrategia. |
| `get_icon()` | **Un único emoji** que acompaña al nombre. |
| `choose_move(state)` | La jugada que quieres hacer, como `(fila, columna)`. |

Y una cosa opcional, `create(seed)`: si tu bot usa azar, créalo con su propio generador de
números (`random.Random(seed)`) como en el ejemplo. Así, con la misma semilla, el bot repite las
mismas decisiones y las partidas se pueden reproducir. Si tu bot no usa azar, no escribas nada.

### Qué recibe `choose_move`

Recibe un `GameState`, la posición completa:

- `state.board[fila][columna]` vale `1` (negras), `-1` (blancas) o `0` (vacía).
- `state.player` es **tu color** en este turno (`1` o `-1`).
- Es inmutable: no puedes modificarlo, y si lo intentas tu bot pierde la partida.

Solo se te pide jugada cuando tienes al menos una jugada legal. Las funciones del motor que más
te servirán son `legal_moves(state)`, `apply_move(state, jugada)` (devuelve el estado siguiente
sin tocar el tuyo) y `score(state)`. Están todas en la
[referencia del motor](referencia/motor.md).

### Las reglas que debe cumplir tu bot

- **Devolver siempre una jugada legal**, como `(fila, columna)` con números del 0 al 7.
- **No modificar** el estado que recibe.
- **Un nombre único.** El proyecto rechaza un nombre que ya use otro jugador.
- **Solo la biblioteca estándar de Python y `reversibounty`.** Nada de librerías externas.
- **Sin red, sin archivos, sin procesos.** Tu `choose_move` debe depender solo del tablero.
- **Ser razonablemente rápido.** Un bot que se cuelga no puede jugar un torneo.

!!! warning "Un bot que incumple las reglas pierde"
    Si tu bot lanza una excepción o devuelve una jugada ilegal, pierde esa partida. Y si esto
    ocurre en los tests, tu pull request no se podrá fusionar.

## 4. Regístralo

Nada se descubre solo. Para que tu bot entre, añádelo a `players/custom/players.yaml`, que ahora
está vacío (`players: []`). Déjalo así:

```yaml title="players/custom/players.yaml"
players:
  - file: esquinero.py
    class: Esquinero
```

`file` es el archivo, que se busca junto a la lista, y `class` es el nombre de tu clase. El nombre,
los autores y el emoji **no se escriben aquí**: los lee el proyecto de tu clase.

Quien revise tu pull request verá en el mismo cambio tu archivo y esta línea, y esa revisión es la
que decide si tu bot entra.

## 5. Compruébalo en tu ordenador

Tres comprobaciones, de la más rápida a la más completa:

```bash
pytest tests/test_contract.py -v
```

Esta es la **prueba de contrato**: juega varias partidas con tu bot, con negras y con blancas, y
comprueba que cada jugada es legal y que no modifica el estado. Debe aparecer una línea con el
nombre de tu bot, por ejemplo `test_cada_jugador_registrado_cumple_el_contrato[esquinero]`, en
verde. No tienes que escribir ninguna prueba: el registro hace que se ejecute sola.

```bash
pytest -q
ruff check .
```

La primera ejecuta todos los tests del proyecto, y la segunda revisa el estilo del código.
Las dos deben salir sin errores, porque son las mismas comprobaciones que hará GitHub.

Si quieres ver cómo juega, enfréntalo al jugador aleatorio:

```python
from reversibounty import play_game
from reversibounty.bots import RandomPlayer
from reversibounty.manifest import load_players

Esquinero = load_players()["esquinero"]
resultado = play_game(Esquinero.create(seed=1), RandomPlayer.create(seed=2))
print(resultado.winner, resultado.score)  # 1 = ganan las negras, el bot
```

## 6. Abre el pull request

Guarda tu trabajo y súbelo a GitHub:

```bash
git add players/custom
git commit -m "Añade el bot esquinero"
git push -u origin bot-esquinero
```

Entra en tu repositorio en GitHub y pulsa **Compare & pull request**. Rellena la plantilla que
aparece: qué cambia, cómo lo has comprobado y la lista de comprobación. Pulsa **Create pull request**.

## 7. Revisión y fusión

Cuando abres el pull request ocurren dos cosas:

1. **Las comprobaciones automáticas** se ejecutan solas: los tests en dos versiones de Python,
   el estilo y la construcción de la documentación. Tienen que salir en verde. Si alguna sale en
   rojo, el pull request no se puede fusionar: abre el detalle, lee el error, corrígelo, y vuelve a
   subir con `git push`.
2. **Otra persona lo revisa.** Pide la revisión a un miembro del equipo y espera su aprobación. Si
   te pide cambios, hazlos y vuelve a subir.

Cuando los tres checks están en verde y hay una aprobación, se pulsa **Merge pull request**. Tu bot
ya forma parte del proyecto y participará en el torneo.

## Si algo falla

Estos son los errores más habituales y cómo se arreglan:

| Qué ves | Qué significa | Qué hacer |
|---|---|---|
| `no existe el archivo ...` | El nombre de `file` no coincide con tu archivo. | Comprueba que está en `players/custom/` y que el nombre es idéntico. |
| `no existe la clase 'X'` | El nombre de `class` no coincide con tu clase. | Copia el nombre exacto de la clase de tu archivo. |
| `no es una subclase de Player` | Tu clase no hereda de `Player`. | Escribe `class MiBot(Player):`. |
| `no se puede crear: Can't instantiate abstract class ... method 'x'` | Te falta implementar el método `x`. | Impleméntalo (ver la tabla del punto 3). |
| `get_icon() debe devolver un único emoji` | El icono es texto, o son varios emojis. | Devuelve un solo emoji, como `"📐"`. |
| `el nombre 'x' ya lo usa ...` | Otro jugador tiene el mismo nombre. | Cambia `get_name()` por uno único. |
| `devolvió una jugada ilegal` | Tu bot eligió una casilla que no encierra ninguna ficha. | Elige siempre entre las de `legal_moves(state)`. |
| `modificó el estado que recibió` | Tu bot intentó cambiar el tablero. | Trabaja con copias, o con `apply_move`, que devuelve un estado nuevo. |
| `lanzó RuntimeError: ...` | Tu bot falló con una excepción. | Lee el mensaje, que dice qué línea y qué error, y corrígelo. |
| `falla al importarse` | Tu archivo da un error nada más cargarlo. | Ejecútalo con `python players/custom/tu_bot.py` y mira el error. |
| `ruff` da avisos | Problemas de estilo. | Ejecuta `ruff check . --fix` y revisa lo que quede. |

!!! tip "Una idea para mejorar tu bot"
    Cambia `choose_move` por algo que mire el futuro: prueba cada jugada con `apply_move`, mira
    cuántas fichas tendrías con `score` y quédate con la mejor. Cuando tengas una versión, juega
    varias partidas contra el jugador aleatorio y comprueba que le ganas casi siempre.

## Referencia

- [La API de jugadores](referencia/jugadores.md): la clase `Player` al detalle.
- [El motor del juego](referencia/motor.md): las funciones para consultar y jugar el tablero.
- [El ejecutor de partidas](referencia/partidas.md): `play_game`, y qué pasa cuando un bot falla.
- [El registro de jugadores](referencia/registro.md): cómo se admite un bot y qué se valida.
- [Las reglas del juego](reglas.md): cómo se juega al Reversi.
