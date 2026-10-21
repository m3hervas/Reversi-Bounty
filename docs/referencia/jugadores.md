# La API de jugadores

Un bot es una subclase de `Player` que dice quién es e implementa **un único método**,
`choose_move`. Esta página se genera automáticamente a partir de los docstrings de
`reversibounty.player`.

!!! note "Qué ve un jugador"
    El Reversi es un juego de información perfecta: los dos jugadores ven el tablero completo
    y no hay azar. Por eso el bot recibe el estado entero (`GameState`), que además es
    inmutable y no se puede estropear.

::: reversibounty.player
