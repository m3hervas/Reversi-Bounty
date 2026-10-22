# El torneo

El torneo decide qué bot es mejor. Es una **liguilla**: cada jugador registrado se enfrenta a
todos los demás, con los dos colores y durante varias rondas. Las partidas se juegan con
[`play_game`](partidas.md) sin modificarlo. Esta página se genera en parte a partir de los
docstrings de `reversibounty.tournament`.

## Cómo se lanza

Con el proyecto instalado y el entorno activado:

```bash
reversi-tournament
```

Imprime la clasificación en el terminal y la guarda en `results/leaderboard.json`. Cada
ejecución regenera el archivo desde cero.

| Opción | Qué hace | Por defecto |
|---|---|---|
| `--semilla N` | El número del que sale toda la aleatoriedad. | `0` |
| `--rondas N` | Cuántas partidas juega cada pareja con cada color. | `5` |
| `--limite S` | Segundos que tiene cada jugador para cada jugada. | `1` |
| `--salida RUTA` | Dónde guardar la clasificación. | `results/leaderboard.json` |
| `--jugadores DIR` | Carpeta con `builtin/` y `custom/`. | `players/` del repositorio |

## Puntos y desempates

Una victoria vale **1 punto**, un empate **0,5** y una derrota **0**. Si dos jugadores empatan a
puntos, va delante el de mayor **diferencia de fichas** (las suyas menos las del rival al final
de cada partida), después el que tenga más victorias y, por último, el orden alfabético.

## El mismo número, el mismo torneo

Toda la ejecución sale de un único número, la semilla. La semilla de cada partida se calcula
a partir de la semilla del torneo, la ronda y los nombres de los dos jugadores. Por eso:

- el mismo torneo produce el mismo resultado dos veces seguidas;
- añadir un bot nuevo no cambia las partidas que ya jugaban los demás entre sí.

## Un bot malo solo se perjudica a sí mismo

El torneo se ejecuta sin supervisión y con código de otras personas dentro. Cada petición de
jugada pasa por una capa de protección, `GuardedPlayer`, además de las comprobaciones que ya
hace `play_game`:

| Conducta del bot | Quién la detecta | Motivo registrado |
|---|---|---|
| Lanza una excepción | `play_game` | `lanzó RuntimeError: ...` |
| Devuelve una jugada ilegal o nada | `play_game` | `devolvió una jugada ilegal: ...` |
| No devuelve nunca | `GuardedPlayer` | `lanzó TimeoutError: no respondió en 1 s` |
| Intenta cerrar el programa con `sys.exit()` | `GuardedPlayer` | `lanzó RuntimeError: intentó terminar el programa...` |
| Modifica el estado que recibe | Python (`frozen`) o `GuardedPlayer` | `lanzó FrozenInstanceError...` o `modificó el estado que recibió` |
| Cambia de nombre durante el torneo | El torneo, antes de cada partida | `cambió su nombre a ...` |
| Falla al crearse | El torneo, antes de cada partida | `no se pudo crear: ...` |

En todos los casos el infractor **pierde esa partida**, el motivo queda guardado y el torneo
sigue con el siguiente emparejamiento.

!!! warning "Un bot colgado sigue vivo en segundo plano"
    Python no puede detener un hilo. Un bot que se pasa del tiempo pierde la partida y el
    torneo continúa, pero su hilo sigue ejecutándose hasta que termine. Si está en un bucle
    infinito, consume CPU y hace más lentas las partidas siguientes, aunque no las detiene.
    Aislarlo del todo exigiría ejecutar cada bot en su propio proceso.

## El archivo `leaderboard.json`

```json
{
  "schema_version": 1,
  "finished_at": "2026-10-22T09:30:00+00:00",
  "seed": 0,
  "rounds": 5,
  "time_limit": 1.0,
  "standings": [
    {
      "rank": 1,
      "name": "avaricioso",
      "icon": "💰",
      "authors": ["Reversi Bounty"],
      "description": "Captura lo máximo posible, ...",
      "played": 10, "wins": 10, "draws": 0, "losses": 0, "forfeits": 0,
      "points": 10.0,
      "discs_for": 420, "discs_against": 180, "disc_diff": 240,
      "forfeit_reasons": []
    }
  ],
  "games": [
    {
      "round": 1,
      "black": "aleatorio",
      "white": "avaricioso",
      "seeds": [123, 456],
      "winner": "avaricioso",
      "score": [20, 44],
      "moves": ["d3", "c5", "..."],
      "forfeit": null
    }
  ]
}
```

*Ejemplo con valores ilustrativos.*

- **`standings`** está ya ordenada: una página puede dibujar la tabla sin calcular nada.
- **`games`** guarda cada partida con sus jugadas en notación `d3`, así que cualquiera se puede
  reproducir. `winner` es `null` si hubo empate, y `forfeit` explica la infracción, si la hubo.
- **`schema_version`** cambia si cambia la forma del archivo, para que quien lo lea lo sepa.

::: reversibounty.tournament
