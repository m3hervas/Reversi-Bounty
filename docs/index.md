# Reversi Bounty

Reversi (Othello) para humanos y bots: un motor de juego en Python, una web para jugar
contra la IA desde el navegador, una API para programar tu propio bot y un torneo automático
con clasificación de recompensas.

Práctica de **Inteligencia Artificial, 3º MAT-A, CUNEF Universidad 2026/27**.

## Qué hay en el proyecto

| | Parte | Qué hace |
|---|---|---|
| 🐍 | **Librería** `reversibounty` | El [motor del juego](referencia/motor.md) (reglas, jugadas legales, volteos, paso de turno y final), la [API de jugadores](referencia/jugadores.md), el [registro](referencia/registro.md) y el [ejecutor de partidas](referencia/partidas.md). |
| 🤖 | **Bots** | Tres [rivales](rivales.md) de referencia y una clase `Player` que cualquiera puede implementar: hay un [tutorial paso a paso](tutorial.md). |
| 🏆 | **Torneo automático** | Todos contra todos, con los dos colores. GitHub Actions lo juega cada noche y publica la clasificación en el [marcador](https://m3hervas.github.io/Reversi-Bounty/#/marcador). Ver [el torneo](referencia/torneo.md). |
| 🌐 | **Web** | [Jugar en el navegador](https://m3hervas.github.io/Reversi-Bounty/), sin instalar nada: contra un bot, entre dos personas o bot contra bot. Ver [el diseño de la web](diseno-jugar.md). |

!!! tip "Una sola fuente de verdad"
    Las reglas y los bots se escriben una vez, en Python. Ese mismo código corre en los tests,
    en el torneo de GitHub Actions y en tu navegador, con [Pyodide](https://pyodide.org): la web
    no reimplementa ninguna regla en JavaScript, solo pregunta al motor y dibuja la respuesta.

## Instalación

```bash
git clone https://github.com/m3hervas/Reversi-Bounty.git
cd Reversi-Bounty
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Jugar en la terminal

Dos personas pueden jugar una partida completa desde la consola, sin web ni interfaz gráfica.

**Qué hay que ejecutar**, con el proyecto instalado y el entorno activado:

```bash
reversi-play          # solo texto, funciona en cualquier terminal
reversi-play-color    # tablero con colores y fichas grandes
```

**Cómo se juega:**

1. Al empezar, el juego muestra unas instrucciones.
2. En tu turno, las casillas donde puedes jugar están marcadas en el tablero.
3. Escribe una de ellas, por ejemplo `d3`, y pulsa Enter.
4. Las fichas del rival que quedan encerradas se dan la vuelta.
5. Si alguien no tiene jugadas, pasa el turno, y el juego avisa.
6. Gana quien tenga más fichas cuando ninguno de los dos pueda mover.

**Comandos durante la partida:** `?` muestra la ayuda y `q` sale.

!!! tip "Si los colores no se ven bien"
    Usa `reversi-play`, que muestra solo texto y no depende de la fuente ni de los colores
    de la terminal.

## Jugar desde Python

Dos jugadores aleatorios, con semilla para que la partida se repita:

```python
from reversibounty import play_game
from reversibounty.bots import RandomPlayer

resultado = play_game(RandomPlayer.create(seed=1), RandomPlayer.create(seed=2))
print(resultado.winner, resultado.score)  # -1 (29, 35): ganan las blancas
```

`resultado.winner` vale `1` si ganan las negras, `-1` si ganan las blancas y `0` si hay empate.
Más detalles en la referencia de [las partidas](referencia/partidas.md).

La misma partida, jugada a jugada, con dos rivales del registro:

```python
from reversibounty import apply_move, initial_state, is_terminal, move_to_str, score
from reversibounty.manifest import load_players

jugadores = load_players()
zeff = jugadores["Zeff minimax"].create(seed=1)
wapol = jugadores["Wapol voraz"].create(seed=2)

state = initial_state()
while not is_terminal(state):
    bot = zeff if state.player == 1 else wapol   # 1 = negras, -1 = blancas
    move = bot.choose_move(state)
    print(move_to_str(move), end=" ")
    state = apply_move(state, move)
print("\nFichas (negras, blancas):", score(state))
```

`play_game` hace lo mismo y, además, da por perdida la partida de un bot que falle o haga una
jugada ilegal.

## Jugar un torneo

Todos los bots registrados, todos contra todos y con los dos colores:

```bash
reversi-tournament
```

Imprime la clasificación y la guarda en `results/leaderboard.json`. Con la misma semilla
(`--semilla`), el resultado es siempre el mismo. Más detalles en [el torneo](referencia/torneo.md).

## La web en tu ordenador

```bash
python scripts/build_web.py          # empaqueta el motor y los bots en web/py.zip
python -m http.server 8000 -d web    # abre http://localhost:8000
```

No abras `index.html` con doble clic: con `file://` el navegador no deja arrancar Python.
Vuelve a ejecutar `build_web.py` cada vez que cambies el motor, un bot o `web/webglue.py`.

## Estructura del repositorio

```
src/reversibounty/        motor (game), API de jugadores (player), partidas (match),
                          registro (manifest), torneo, medición de bots (benchmark) y terminal
src/reversibounty/bots/   las estrategias de Buggy, Wapol y Zeff
players/builtin/          los bots de referencia y la lista que los admite
players/custom/           los bots enviados por pull request y su lista
web/                      la web de GitHub Pages (Pyodide + JavaScript que solo dibuja)
docs/                     esta documentación (MkDocs + Material, en Read the Docs)
tests/                    los tests (pytest)
.github/workflows/        tests, documentación, torneo nocturno y publicación de la web
```

La clasificación no vive en `main`: el torneo la guarda en la rama
[`marcador`](https://github.com/m3hervas/Reversi-Bounty/tree/marcador), porque `main` solo
admite cambios por pull request aprobado. Ver [dónde se publica la clasificación](referencia/torneo.md#donde-se-publica-la-clasificacion).
