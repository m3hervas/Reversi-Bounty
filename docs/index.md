# Reversi Bounty

Reversi (Othello) para humanos y bots: un motor de juego en Python, una web para jugar
contra la IA desde el navegador, una API para programar tu propio bot y un torneo automático
con clasificación de recompensas.

Práctica de **Inteligencia Artificial, 3º MAT-A, CUNEF Universidad 2026/27**.

## Qué hay en el proyecto

| Parte | Qué hace |
|---|---|
| Motor del juego | Reglas, jugadas legales, volteos, paso de turno y final de partida. |
| API de bots | Una clase `Player` que cualquiera puede implementar para escribir su bot. |
| Torneo | Todos contra todos, con ambos colores, y clasificación. |
| Web | Jugar contra la IA en el navegador, sin instalar nada. |

!!! note "Estado"
    La documentación crece con el proyecto. Por ahora están disponibles las
    [reglas del juego](reglas.md) y la referencia del [motor del juego](referencia/motor.md).

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
