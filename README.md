# Reversi-Bounty

[![Docs](https://readthedocs.org/projects/reversi-bounty/badge/?version=latest)](https://reversi-bounty.readthedocs.io)

Reversi (Othello) para humanos y bots: motor en Python, web para jugar contra la IA en el navegador, API para programar tu propio bot y torneo automático con clasificación de recompensas. Práctica de IA, CUNEF 2026/27.

## Jugar en la terminal

Dos personas pueden jugar una partida completa de Reversi desde la consola, sin web.

1. Instala el proyecto (solo la primera vez):

   ```bash
   git clone https://github.com/m3hervas/Reversi-Bounty.git
   cd Reversi-Bounty
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

   En Linux o macOS, el entorno se activa con `source .venv/bin/activate`.

2. Lanza el juego con uno de estos dos comandos:

   ```bash
   reversi-play          # solo texto, funciona en cualquier terminal
   reversi-play-color    # tablero con colores y fichas grandes
   ```

3. Al empezar verás las instrucciones. En tu turno, escribe una casilla marcada en el tablero, por ejemplo `d3`, y pulsa Enter. Escribe `?` para ver la ayuda y `q` para salir.

Los comandos se instalan con el paquete, así que también funcionan con un simple `pip install` sin clonar el repositorio.

## Jugar en el navegador

**Sin instalar nada: <https://m3hervas.github.io/Reversi-Bounty/>**

La carpeta `web/` es una página estática en la que una persona juega contra cualquier bot del
registro. No reimplementa ninguna regla: ejecuta en el navegador, con
[Pyodide](https://pyodide.org), el mismo paquete `reversibounty` que usan los tests.

Para verla en tu ordenador:

```bash
python scripts/build_web.py          # empaqueta el motor en web/py.zip
python -m http.server 8000 -d web    # sirve la carpeta web/
```

Abre <http://localhost:8000>. No abras `index.html` con doble clic: con `file://` el navegador
no deja arrancar el motor. Vuelve a ejecutar `build_web.py` cada vez que cambies el motor, un bot
o `web/webglue.py`. `web/py.zip` es un archivo generado y no se sube al repositorio.

Desde la consola del navegador se puede preguntar al motor de Python directamente:

```js
const inicio = await RB.engine.call("new_game");
await RB.engine.call("legal_moves", [inicio.state]);  // [[2,3],[3,2],[4,5],[5,4]]
```

## Jugar desde Python

Con el proyecto instalado, se puede jugar sin la terminal. Dos jugadores aleatorios, con
semilla para que la partida se repita:

```python
from reversibounty import play_game
from reversibounty.bots import RandomPlayer

resultado = play_game(RandomPlayer.create(seed=1), RandomPlayer.create(seed=2))
print(resultado.winner, resultado.score)  # -1 (29, 35): ganan las blancas
print(resultado.moves[:4])                # las primeras jugadas, como (fila, columna)
```

`resultado.winner` vale `1` si ganan las negras, `-1` si ganan las blancas y `0` si hay empate.
`resultado.forfeit` es `None` si la partida acabó con normalidad, o explica por qué perdió un
jugador que hizo una jugada ilegal o lanzó una excepción.

Y el mismo bucle a mano, usando solo las funciones del motor:

```python
from reversibounty import apply_move, initial_state, is_terminal, legal_moves, score, winner

state = initial_state()
while not is_terminal(state):
    state = apply_move(state, legal_moves(state)[0])  # siempre la primera jugada legal

print(state)
print(score(state), winner(state))
```

El nombre del paquete es `reversibounty`, todo junto y sin guion bajo.

## Escribir un bot

Un bot es una subclase de `Player` que declara su nombre, autores, descripción y un emoji, e
implementa un único método, `choose_move`. Se añade como un archivo en `players/custom/` y una
línea en `players/custom/players.yaml`, y se envía por pull request.

Hay un **[tutorial paso a paso](https://reversi-bounty.readthedocs.io/es/latest/tutorial/)**, con
un bot de ejemplo completo, que va desde clonar el proyecto hasta tener el bot fusionado. Las
comprobaciones automáticas (tests, estilo y la prueba de contrato) dicen si tu bot cumple las
reglas antes de que nadie lo revise.

La referencia de la API (`Player`, el motor, `play_game` y el registro) está en la
[documentación](https://reversi-bounty.readthedocs.io).
