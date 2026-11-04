# Los rivales

Los bots de referencia del proyecto. Los tres están admitidos en `players/builtin/players.yaml`,
juegan el torneo nocturno y se pueden elegir como rival en la
[web](https://m3hervas.github.io/Reversi-Bounty/#/jugar).

| | Bot | Cómo decide | Cuánto mira hacia delante |
|---|---|---|---|
| 👨‍🍳 | **Zeff minimax** | Minimax con poda alfa-beta. Valora las casillas (esquinas muy buenas, sus vecinas malas) y la movilidad; en una posición final solo cuenta la diferencia de fichas. [Cómo funciona](bot-minimax.md). | Profundidad iterativa: 1, 2, 3… jugadas, hasta agotar 0,5 s por jugada |
| 😈 | **Wapol voraz** | Puntúa cada jugada por las fichas que captura, el valor de la casilla, las esquinas que deja al rival y las jugadas que le quedan al rival. Desempata al azar. | Ninguna: solo la jugada actual |
| 🃏 | **Buggy aleatorio** | Una jugada legal al azar, con su propio generador y semilla. La vara de medir. | Ninguna |

## Quién gana a quién

Torneo del 03/11/2026: 5 rondas, cada pareja con los dos colores, 1 s por jugada.

| Bot | Victorias | Derrotas | Diferencia de fichas |
|---|---|---|---|
| 👨‍🍳 Zeff minimax | 19 | 1 | +490 |
| 😈 Wapol voraz | 10 | 10 | +48 |
| 🃏 Buggy aleatorio | 1 | 19 | −538 |

Zeff ganó 10 de 10 a Buggy y 9 de 10 a Wapol; Wapol ganó 9 de 10 a Buggy. La clasificación al
día, que el torneo vuelve a jugar cada noche, está en el
[marcador](https://m3hervas.github.io/Reversi-Bounty/#/marcador).

Para medirlos tú mismo, en los dos sentidos y con semilla fija:

```bash
python -m reversibounty.benchmark --partidas 20
```

## Añadir el tuyo

Cualquiera puede añadir un rival por pull request, sin tocar el código del juego: sigue el
[tutorial](tutorial.md).
