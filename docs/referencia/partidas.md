# El ejecutor de partidas

`play_game` juega una partida completa entre dos jugadores y devuelve el ganador junto con
la lista de jugadas. No sabe nada de personas, bots ni torneos: solo necesita objetos con un
método `choose_move`. Esta página se genera automáticamente a partir de los docstrings de
`reversibounty.match`.

!!! note "Qué pasa si un bot hace trampas o falla"
    Cada jugada se valida antes de aplicarla. Si un jugador lanza una excepción o devuelve una
    jugada ilegal, **pierde esa partida** y el motivo queda en `forfeit`, pero el programa
    sigue funcionando. Así un bot roto no puede estropear un torneo ni a los demás jugadores.

::: reversibounty.match
