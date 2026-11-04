# El bot minimax (👨‍🍳 Zeff minimax)

Esta página explica cómo decide su jugada el bot `Zeff minimax`, con el detalle suficiente para
que alguien ajeno al equipo pueda reimplementarlo. El código está en
`src/reversibounty/bots/zeff_minmax.py` y su libro de aperturas en
`src/reversibounty/bots/zeff_libro.py`.

## La idea en una frase

Antes de jugar, el bot imagina sus jugadas posibles, las respuestas del rival, sus
contrarrespuestas, y así varios turnos hacia delante. Valora cómo queda el tablero al final de
cada línea y elige la jugada que le deja mejor **suponiendo que el rival responde lo mejor que
puede**. Cuando quedan pocas casillas, en lugar de valorar calcula la partida hasta el final.

## Cómo piensa una jugada, paso a paso

1. **¿Solo hay una jugada legal?** La juega sin pensar.
2. **¿La posición está en el libro de aperturas?** Juega la jugada del libro al instante (ver
   [el libro](#el-libro-de-aperturas)).
3. **Si no, se da 0,5 s.** El torneo concede 1 s por jugada; la otra mitad es margen.
4. **Profundización iterativa.** Busca primero a profundidad 1 (solo su jugada), luego 2 (su
   jugada y la respuesta del rival), luego 3, y así sucesivamente. Se queda con la mejor jugada de
   la **última profundidad que llegó a terminar**. Si el tiempo se acaba a mitad de una
   profundidad, descarta esa búsqueda a medias y usa la anterior: nunca se pasa del tiempo ni juega
   con un análisis incompleto.
5. **Minimax (en forma *negamax*).** En sus turnos elige el valor más alto y en los del rival el más
   bajo. Se escribe una sola vez gracias a que lo bueno para uno es igual de malo para el otro: el
   valor de una posición es el máximo de «menos el valor» de las posiciones siguientes.
6. **Poda alfa-beta.** Si una rama ya se sabe peor que otra que se ha mirado, se deja de explorar:
   no puede cambiar la decisión. Da el mismo resultado que minimax sin poda, pero mira muchas menos
   posiciones.
7. **Pasar turno.** Si a quien le toca no tiene jugadas, el turno pasa al rival sin gastar
   profundidad; si ninguno puede jugar, la partida ha terminado y se cuenta el resultado exacto.
8. **Final exacto.** La profundidad sigue creciendo mientras haya tiempo. Si en una vuelta
   **todas** las ramas llegan al final de la partida, el resultado ya no es una estimación sino un
   cálculo exacto, y el bot para: juega perfecto desde ahí.
9. **Empates.** Si varias jugadas valen exactamente lo mismo, elige una al azar con la semilla de
   la partida. Con la misma semilla juega igual, siempre que le dé tiempo a la misma profundidad.

## Por qué ahora mira más lejos que antes

La primera versión de Zeff evaluaba unas 3.500 posiciones por segundo y en el medio juego solo
veía 3 o 4 jugadas por delante. La versión actual mira unas 10 veces más posiciones en el mismo
tiempo, por tres cambios:

| Cambio | Qué hace | Por qué ayuda |
|---|---|---|
| **Tablero en bits** | Dentro de la búsqueda, el tablero son dos números de 64 bits: uno con las fichas de quien mueve y otro con las del rival (bit `fila × 8 + columna`). Las jugadas legales se calculan desplazando esos bits en las 8 direcciones a la vez, y los volteos igual. | Python hace cada operación con los 64 bits de golpe, en lugar de recorrer el tablero casilla a casilla. Los tests comprueban que da exactamente las mismas jugadas y volteos que el motor del juego. |
| **Orden de las jugadas** | En cada posición prueba primero la jugada que fue la mejor la última vez que la vio, y después las casillas buenas antes que las malas (esquinas primero, casillas X al final). En la raíz, la mejor jugada de la profundidad anterior va la primera. | La poda alfa-beta descarta más cuanto antes encuentra la jugada buena. Con buen orden se mira una fracción de las posiciones. |
| **Tabla de transposición** | Un diccionario que guarda, para cada posición ya analizada, su valor, a qué profundidad, si es exacto o una cota, y cuál fue la mejor jugada. | A la misma posición se llega por caminos distintos (jugar A y luego B o B y luego A), y cada vuelta de la profundización iterativa repite las anteriores. Lo guardado se reutiliza. Se vacía en cada jugada para no crecer sin límite. |

## Qué evalúa

Cuando la búsqueda llega a su profundidad sin acabar la partida, puntúa el tablero desde el punto
de vista de quien mueve:

| Parte | Cómo se calcula | Por qué |
|---|---|---|
| Casillas | Esquinas +120, bordes +12 y +6, interior +2, segunda línea −3, por cada ficha propia (las del rival restan). | Una esquina nunca se puede voltear; los bordes son difíciles de voltear. |
| Casillas X y C | La casilla en diagonal a una esquina (X) resta 50 y las dos de al lado (C) restan 20, **solo mientras esa esquina está vacía**. | Ocuparlas permite al rival coger la esquina. Cuando la esquina ya está ocupada, dejan de ser peligrosas. |
| Movilidad | `peso × 10 × (mis jugadas − las del rival) / (mis jugadas + las del rival)`. | Quien tiene más opciones acaba obligando al otro a jugar mal. |
| Frontera | Igual, con las fichas que tocan alguna casilla vacía; tener **menos** es lo bueno. | Las fichas de frontera le dan jugadas al rival. |
| Fichas | Diferencia de fichas, **solo en el final**. | Al principio, tener muchas fichas suele ser malo; al final es lo único que cuenta. |
| Partida terminada | `±100 000` más la diferencia de fichas. | Ganar pesa más que cualquier otra cosa. |

Los pesos de movilidad, frontera y fichas cambian con la fase de la partida:

| Fase | Casillas vacías | Movilidad | Frontera | Fichas |
|---|---|---|---|---|
| Apertura | más de 44 | 12 | 6 | 0 |
| Medio juego | de 21 a 44 | 8 | 4 | 0 |
| Final | 20 o menos | 4 | 1 | 6 |

## El libro de aperturas

Las primeras jugadas son las más difíciles de calcular: el tablero está casi vacío, hay muchas
opciones y el final queda muy lejos. El libro guarda la jugada para todas las posiciones que pueden
salir en las **5 primeras jugadas** de una partida, calculada por el propio Zeff con **5 s de
análisis por posición** en lugar de 0,5 s. En la partida, esas jugadas salen al instante.

- **Simetrías.** Girar o reflejar el tablero no cambia el juego, así que de cada familia de
  posiciones simétricas solo se guarda una (la «canónica»). Al consultar, se gira la posición, se
  busca y se deshace el giro de la jugada.
- **Cómo se regenera:** `python scripts/generar_libro_zeff.py` (o con `--jugadas` y
  `--segundos` para cambiar su tamaño). Hay que regenerarlo si cambia la evaluación.

## Una corrección: los empates de la raíz

La primera versión elegía al azar entre las jugadas que «empataban» como mejores, pero con la poda
alfa-beta una jugada peor podía devolver justo el mismo valor como **cota** y colarse como empate:
pasaba en unas 7 de cada 39 posiciones de prueba. Ahora cada jugada de la raíz se busca con la
ventana `(mejor − 1, +∞)`, así que una jugada igual de buena devuelve su valor exacto y una peor
devuelve algo menor. Un test lo comprueba comparando con la búsqueda sin poda.

## Cuánto mira hacia delante

Depende del tiempo y de la máquina, no de un número fijo. Medido en un portátil, en partidas contra
Wapol voraz, con el ordenador sin otra carga:

| Fase | Profundidad media | Tiempo medio por jugada |
|---|---|---|
| Apertura (más de 44 vacías) | 6,7 jugadas (las 5 primeras jugadas salen del libro, al instante) | 0,48 s |
| Medio juego | 5,9 jugadas | 0,48 s |
| Final (16 vacías o menos) | resuelve la partida hasta el final en la mayoría de las jugadas | 0,20 s |

Ninguna jugada pasó de 0,5 s. Con el ordenador ocupado en otras cosas la profundidad baja (en una
medición con otros programas en marcha, el medio juego se quedó en 4,8 jugadas), y en la web, donde
Python va más lento, también.

## Dónde juega mal

- **Efecto horizonte.** En el medio juego solo ve hasta su profundidad. Si hay una jugada
  desastrosa justo más allá, no la ve.
- **Evaluación hecha a mano.** Los pesos de la tabla se han elegido con criterio y probado contra la
  versión anterior, pero no se han ajustado de forma sistemática (por ejemplo, con miles de partidas
  contra sí mismo).
- **No es repetible entre máquinas.** Como la profundidad depende del tiempo, la misma semilla puede
  dar partidas distintas en dos ordenadores, o en la web, donde Python va más lento.
- **El libro es corto.** Solo cubre las 5 primeras jugadas y lo ha calculado el propio Zeff, así que
  hereda los fallos de su evaluación.
- **La movilidad es aproximada**: cuenta las jugadas del rival aunque en la posición real no le toque.

## Qué hay que escribir para reimplementarlo

Un `Player` con las cuatro funciones de identidad (nombre `Zeff minimax`, icono 👨‍🍳, autor y una
descripción), un `create(seed)` que guarde un `random.Random(seed)`, y un `choose_move` con los
pasos de arriba. Los valores están en las constantes del módulo: `DEFAULT_TIME_LIMIT = 0.5`,
`MAX_DEPTH = 64`, `CASTIGO_X = 50`, `CASTIGO_C = 20`, la tabla `FASES` y los pesos de las
casillas. El tablero en bits puede sustituirse por el motor del juego (`legal_moves`,
`apply_move`): el bot pensaría exactamente igual, solo que unas 10 veces más despacio.

## Cómo se ha medido

Cada enfrentamiento se jugó mitad de partidas con cada color, con semillas fijas y con la misma capa
de protección que el torneo (`GuardedPlayer`, 1 s por jugada):

| Rival | Partidas | Victorias | Empates | Derrotas | Diferencia media de fichas |
|---|---|---|---|---|---|
| Zeff v1 (la versión anterior) | 40 | 35 | 1 | 4 | +31 |
| Wapol voraz | 40 | 40 | 0 | 0 | +48 |
| Buggy aleatorio | 20 | 20 | 0 | 0 | +55 |

Contra la versión anterior, 20 partidas se jugaron sin libro de aperturas (18 victorias, 1 empate, 1
derrota) y 20 con libro (17 victorias, 3 derrotas). Ninguna partida se perdió por infracción ni por
tiempo.

Para medirlo tú mismo contra los demás bots del registro, en los dos sentidos:

```bash
python -m reversibounty.benchmark --partidas 40 --jugadores "Buggy aleatorio" "Wapol voraz" "Zeff minimax"
```

## Referencia

::: reversibounty.bots.zeff_minmax
