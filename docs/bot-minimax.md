# El bot minimax (🧠 zeff-minimax)

Esta página explica cómo decide su jugada el bot `zeff-minimax`, con el detalle suficiente
para que alguien ajeno al equipo pueda reimplementarlo. El código está en
`src/reversibounty/bots/zeff_minmax.py`.

## La idea en una frase

Antes de jugar, el bot imagina sus jugadas posibles, las respuestas del rival, sus
contrarrespuestas, y así varios turnos hacia delante. Valora cómo queda el tablero al final
de cada línea y elige la jugada que le deja mejor suponiendo que el rival responde lo mejor
que puede.

## Cómo decide, paso a paso

1. **Presupuesto de tiempo.** Al empezar a pensar fija una hora límite: 0,5 s desde ese
   momento. El torneo da 1 s por jugada, y la mitad que sobra es margen de seguridad.
2. **Profundización iterativa.** Busca primero a profundidad 1 (solo su jugada), luego a 2 (su
   jugada y la respuesta del rival), luego a 3, y así hasta la profundidad 8 como máximo. Se
   queda con la mejor jugada de la **última profundidad que llegó a terminar**.
3. **Si se acaba el tiempo a mitad de una profundidad**, descarta esa búsqueda a medias y usa
   el resultado de la anterior. Así nunca se pasa del tiempo ni juega con un análisis
   incompleto.
4. **Minimax.** En los turnos del bot se elige el valor más alto; en los del rival, el más
   bajo (el rival intenta lo contrario). Quién mueve se mira siempre en el estado de la
   partida, porque el motor pasa el turno solo cuando alguien no tiene jugadas.
5. **Poda alfa-beta.** Si una rama ya se sabe peor que otra que se ha mirado, se deja de
   explorar, porque no puede cambiar el resultado. Da el mismo resultado que minimax a secas,
   pero mira bastante menos posiciones.
6. **Orden de las jugadas.** En la raíz se miran primero las esquinas, para que la poda
   funcione mejor.
7. **Empates.** Si varias jugadas valen lo mismo, elige una al azar con la semilla de la
   partida. Con la misma semilla juega igual (siempre que le dé tiempo a la misma
   profundidad, ver más abajo).
8. **Jugada de emergencia.** Si ni siquiera terminara la profundidad 1, juega una jugada
   legal al azar. Con una sola jugada legal, la juega sin pensar.

## Qué evalúa

Cuando la búsqueda llega a su profundidad máxima, el tablero se puntúa **desde el punto de
vista del bot**:

| Parte | Cómo se calcula |
|---|---|
| Casillas | Suma de la tabla de pesos (`SQUARE_WEIGHTS`, la misma que usa el bot avaricioso): esquinas +100, las casillas pegadas a una esquina negativas (-20 y -50), bordes algo positivos. Las fichas del rival restan. |
| Movilidad | `5 × (mis jugadas legales − las del rival)`. Tener más opciones que el rival es una ventaja. |
| Final de partida | Si la posición es terminal, solo cuenta la diferencia de fichas, más o menos 100 000 según gane o pierda. Ganar pesa siempre más que cualquier otra cosa. |

## Cuánto mira hacia delante

Entre 1 y 8 jugadas, según el tiempo. Cuántas llega a mirar **depende de la máquina y de lo
ocupada que esté**, porque el límite es de tiempo y no de profundidad. No he medido la
profundidad media que alcanza en cada fase de la partida, así que no doy cifras.

## Dónde juega mal

- **Efecto horizonte.** Solo ve hasta su profundidad. Si hay una derrota forzada más allá,
  no la ve, y puede ir a una línea que parece buena justo antes de que se vuelva mala.
- **Evaluación fija.** Usa la misma tabla de casillas en toda la partida. Las casillas
  "malas" no siempre lo son: en el final, ocupar una puede ser lo correcto, y el bot lo
  evitará.
- **No resuelve el final exacto.** No calcula las últimas jugadas hasta el final con
  seguridad, salvo que le dé tiempo a la profundidad necesaria.
- **No es repetible entre máquinas.** Como la profundidad depende del tiempo, la misma
  semilla puede dar partidas distintas en dos ordenadores, o si el torneo va más lento.
- **Sin memoria.** No guarda posiciones ya analizadas ni libro de aperturas: vuelve a
  calcular desde cero en cada jugada.
- **Movilidad aproximada.** Cuenta las jugadas del rival como si le tocara a él mover, aunque
  en la posición real pudiera no tocarle.

## Qué hay que escribir para reimplementarlo

Un `Player` con las cuatro funciones de identidad (nombre `zeff-minimax`, icono 🧠, autor
y una descripción), un `create(seed)` que guarde un `random.Random(seed)`, y un
`choose_move` con los pasos de arriba. La evaluación y los valores (`DEFAULT_TIME_LIMIT = 0.5`,
`MAX_DEPTH = 8`, `MOBILITY_WEIGHT = 5`) son los de las constantes al principio del archivo.

## Cómo se ha medido

El script de medición compara a este bot con los demás en los dos sentidos:

```bash
python -m reversibounty.benchmark --partidas 40 --jugadores aleatorio avaricioso zeff-minimax
```

## Referencia

::: reversibounty.bots.zeff_minmax
