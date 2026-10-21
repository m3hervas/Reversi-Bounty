# Reglas del juego

El Reversi (también conocido como Othello) es un juego de tablero para **dos jugadores**: uno
lleva las fichas negras y el otro las blancas. Gana quien termina con más fichas de su color
sobre el tablero.

Las reglas caben en **cuatro pasos** y la estrategia básica, en **cinco ideas**. Esta página
explica primero las reglas, después resuelve por escrito los casos dudosos y, por último,
presenta las ideas de estrategia.

!!! note "Sin azar ni información oculta"
    En el Reversi no hay dados, cartas ni nada que dependa de la suerte, y los dos jugadores
    ven siempre el tablero completo. Es un juego **determinista y de información perfecta**:
    la misma jugada en la misma posición produce siempre el mismo resultado, y cada jugador
    sabe en todo momento todo lo que sabe su rival.

## Parte I. Las reglas

### 1. El tablero y la salida

Se juega en un tablero de **8 × 8 casillas** (64 en total) con fichas que son negras por una
cara y blancas por la otra. Cada ficha muestra hacia arriba el color de su dueño en ese
momento; cuando se captura, se le da la vuelta.

Las columnas se nombran con letras, de la `a` a la `h`, y las filas con números, del `1` al
`8`, como en el ajedrez. Cada casilla se escribe con su letra y su número: `d3` es la
columna `d`, fila `3`. La casilla de **arriba a la izquierda es `a1`** y la de abajo a la
derecha, `h8`.

La partida empieza con **cuatro fichas en el centro, colocadas en diagonal**: blancas en `d4`
y `e5`, y negras en `e4` y `d5`.

```text
  a b c d e f g h
1 . . . . . . . .
2 . . . . . . . .
3 . . . . . . . .
4 . . . O X . . .
5 . . . X O . . .
6 . . . . . . . .
7 . . . . . . . .
8 . . . . . . . .
```

*Posición inicial. `X` = ficha negra, `O` = ficha blanca, `.` = casilla vacía.*

**Siempre mueven primero las negras** y, a partir de ahí, los turnos se alternan. En la
posición inicial las negras tienen exactamente cuatro jugadas posibles: `d3`, `c4`, `f5` y
`e6`.

!!! note "La notación en el código"
    En [el motor del juego](referencia/motor.md) una jugada no se escribe como texto, sino
    como una pareja `(fila, columna)` con números del 0 al 7. Así, `d3` equivale a `(2, 3)`:
    fila 3 → índice 2, columna `d` → índice 3. Las funciones `move_to_str` y `str_to_move`
    convierten de una notación a la otra.

### 2. Capturar: encerrar y dar la vuelta

En su turno, el jugador coloca **una ficha de su color en una casilla vacía**. Solo puede
ponerla donde **encierre al menos una ficha rival**: es decir, donde quede una línea recta de
fichas rivales, **sin huecos**, entre la ficha nueva y otra ficha propia que ya estaba en el
tablero. La línea puede ser horizontal, vertical o diagonal.

Todas las fichas encerradas **se dan la vuelta** y pasan a ser del jugador que mueve. Si la
misma jugada encierra fichas en varias direcciones, se dan la vuelta las de **todas** ellas.

Si una casilla vacía no encierra nada en ninguna dirección, **no se puede jugar ahí**. Por
ejemplo, en la posición inicial las negras no pueden jugar en `c3`: aunque está pegada a una
ficha blanca (`d4`), detrás de ella, en esa diagonal, no hay una ficha negra.

**Ejemplo.** Las negras abren con `d3` y las blancas responden con `e3`. Ahora mueven las
negras:

```text
  a b c d e f g h
1 . . . . . . . .
2 . . . . . . . .
3 . . . X O . . .
4 . . . X O . . .
5 . . . X O . . .
6 . . . . . . . .
7 . . . . . . . .
8 . . . . . . . .
```

*Antes de la jugada. Mueven las negras (`X`).*

Si las negras juegan en `f3`, capturan **en dos direcciones a la vez**:

- hacia la izquierda, la ficha blanca de `e3` queda encerrada entre `f3` y la negra de `d3`;
- en diagonal hacia abajo a la izquierda, la de `e4` queda encerrada entre `f3` y la negra de
  `d5`.

```text
  a b c d e f g h
1 . . . . . . . .
2 . . . . . . . .
3 . . . X X X . .
4 . . . X X . . .
5 . . . X O . . .
6 . . . . . . . .
7 . . . . . . . .
8 . . . . . . . .
```

*Después de `f3`. Se han dado la vuelta `e3` y `e4`; `e5` sigue siendo blanca porque no está
encerrada.*

### 3. Si no puedes capturar, pasas

Si el jugador al que le toca **no tiene ninguna jugada que encierre algo**, pierde el turno y
vuelve a mover su rival. Esto puede ocurrir varias veces seguidas.

En cambio, **no se puede pasar por gusto**: si hay al menos una jugada legal, es obligatorio
hacer una.

En nuestro motor el paso de turno es **automático**. Después de cada jugada, el motor
comprueba si el rival puede mover; si no puede, el turno vuelve al mismo jugador. Por eso a un
bot solo se le pide jugada cuando tiene alguna, y la API no necesita una jugada especial para
"pasar".

### 4. El final

La partida termina cuando **ninguno de los dos jugadores puede mover**. Casi siempre ocurre
porque el tablero se ha llenado, pero a veces acaba antes: por ejemplo, cuando uno de los dos
se queda sin fichas.

Entonces se cuentan las fichas de cada color y **gana quien tenga más**. Si los dos tienen las
mismas (por ejemplo, 32 a 32), la partida es **empate**.

## Casos dudosos y cómo los resolvemos

Las reglas anteriores dejan algunas preguntas abiertas. Estas son las respuestas que sigue el
proyecto, y coinciden con lo que hace [el motor del juego](referencia/motor.md).

| Pregunta | Respuesta |
|---|---|
| ¿Qué pasa si un jugador no puede mover pero el otro sí? | El que no puede mover pasa y vuelve a mover el otro. La partida **no** termina. |
| ¿Qué pasa si la partida acaba antes de llenarse el tablero? | Las casillas vacías no cuentan para nadie: se cuentan solo las fichas que hay en el tablero y gana quien tenga más. |
| ¿Cómo se decide un empate? | Si los dos tienen el mismo número de fichas, es empate. No hay desempate. |
| ¿Se puede pasar voluntariamente? | No. No existe la jugada "pasar": solo se pasa cuando no hay ninguna jugada legal, y el motor lo hace solo. |
| ¿Se pueden acabar las fichas de un jugador? | No. Hay tantas fichas como casillas (64), así que nunca faltan. El motor no lleva la cuenta de fichas en la mano de cada jugador. |
| ¿Qué es una jugada ilegal? | Cualquier jugada que no cumpla las reglas: una casilla ocupada, una casilla fuera del tablero, una casilla que no encierra ninguna ficha rival o algo que ni siquiera tiene la forma de una jugada `(fila, columna)`. |
| ¿Qué hace el motor con una jugada ilegal? | `is_legal` devuelve `False` y `apply_move` lanza un error `ValueError`. El motor nunca coloca una ficha en una casilla ilegal. |

**Ejemplo de partida que acaba antes de tiempo.** Con las jugadas `e6 f4 e3 f6 g5 d6 e7 f5 c5`,
las negras se quedan con las 13 fichas del tablero tras solo nueve jugadas:

```text
  a b c d e f g h
1 . . . . . . . .
2 . . . . . . . .
3 . . . . X . . .
4 . . . X X X . .
5 . . X X X X X .
6 . . . X X X . .
7 . . . . X . . .
8 . . . . . . . .
```

*Posición final. Las blancas no tienen fichas y las negras no pueden encerrar nada, así que
nadie puede mover. Ganan las negras 13 a 0, con 51 casillas vacías.*

## Parte II. La estrategia

Las reglas son sencillas, pero jugar bien no lo es. Estas cinco ideas son las que más ayudan a
alguien que empieza, y también las que suelen usar los bots para valorar una posición.

### 5. Las esquinas mandan

Una ficha en una esquina **no se puede voltear nunca**, porque no hay ninguna casilla al otro
lado desde la que encerrarla. Además, las fichas del mismo color que forman una fila continua
con ella a lo largo del borde tampoco se pueden voltear. A estas fichas se las llama
**estables**.

Contar fichas en mitad de la partida engaña, porque muchas cambiarán de color varias veces.
Los buenos jugadores no cuentan fichas: cuentan **fichas que nadie puede quitarles**.

!!! tip "Consejo"
    Si puedes coger una esquina, casi siempre es buena jugada. Y si tu rival puede cogerla en
    su próximo turno, busca una jugada que se lo impida o que le dé algo peor.

### 6. Cuidado con las casillas X

Las **casillas X** son las que están en diagonal a una esquina: `b2`, `g2`, `b7` y `g7`. Si
juegas en una de ellas mientras su esquina está vacía, es fácil que tu rival pueda encerrar la
ficha en diagonal y quedarse con la esquina.

Las **casillas C** son las del borde pegadas a una esquina, como `b1` o `a2` (hay ocho). Son
peligrosas por la misma razón, aunque menos que las casillas X.

!!! warning "Consejo"
    Mientras la esquina esté vacía, evita las casillas X. Las casillas C, úsalas solo cuando
    hayas comprobado que no le das la esquina a tu rival.

### 7. Menos fichas, más jugadas

Al principio y en mitad de la partida lo que importa es la **movilidad**: cuántas jugadas
legales tienes. Quien tiene muchas opciones puede elegir una buena; quien tiene pocas acaba
obligado a jugar donde no quiere, por ejemplo en una casilla X.

Por eso **comer muchas fichas pronto suele ser un error**: cuantas más fichas tuyas hay en el
tablero, más sitios tiene tu rival para encerrar, y más jugadas le das a él.

**Consejo:** antes de mover, compara cuántas jugadas te quedarían a ti y cuántas le dejarías a
tu rival. Muchas veces la mejor jugada es la que voltea menos fichas.

### 8. La frontera

Las fichas de **frontera** son las que tocan alguna casilla vacía. Toda jugada del rival se
hace en una casilla vacía pegada a alguna de tus fichas, así que tus fichas de frontera son
sus puntos de entrada.

Tener pocas fichas de frontera significa darle pocas jugadas al rival, así que esta idea va de
la mano de la anterior.

**Consejo:** prefiere jugadas que volteen fichas del interior de tu grupo y no amplíen la
frontera hacia las casillas vacías.

### 9. Paridad

Hacia el final de la partida, el tablero queda dividido en **zonas** de casillas vacías
separadas entre sí. En una zona con un número **impar** de casillas, quien entra primero suele
ser también quien hace la última jugada en ella, y la última jugada de una zona no se puede
contestar.

No es una regla del juego, sino una costumbre de jugadores de torneo que solo importa en las
últimas jugadas.

**Consejo:** cuando queden pocas casillas, intenta jugar en las zonas impares y deja que tu
rival tenga que abrir las pares.

## Glosario

| Término | Significado |
|---|---|
| Casilla X | Casilla en diagonal a una esquina: `b2`, `g2`, `b7` o `g7`. |
| Casilla C | Casilla del borde pegada a una esquina, como `b1`, `a2`, `g1` o `h2`. |
| Ficha estable | Ficha que ya no se puede voltear hasta el final de la partida, como la de una esquina. |
| Frontera | Conjunto de fichas que tocan al menos una casilla vacía. |
| Movilidad | Número de jugadas legales que tiene un jugador en una posición. |
| Paridad | Idea de que, en una zona con un número impar de casillas vacías, quien entra primero suele hacer la última jugada. |
| Pasar | Perder el turno por no tener ninguna jugada legal. Nunca es voluntario. |
| Notación | Forma de nombrar las casillas: letra de columna (`a`–`h`) y número de fila (`1`–`8`), por ejemplo `d3`. En el código, `(fila, columna)` desde 0, por ejemplo `(2, 3)`. |
