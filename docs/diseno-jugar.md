# Diseño de la pestaña Jugar

Esta página explica **por qué** la pestaña Jugar es como es. Cada decisión tiene una razón, y
casi todas se pueden cambiar tocando un número o un archivo.

## La idea

Jugar al Reversi contra un bot no tiene cara: es un tablero que responde. La pestaña recrea lo que
pasa en una mesa de verdad. **Tú estás a un lado, el rival está al otro y entre los dos hay un
tablero.** El rival es un personaje que reacciona a lo que haces, y el tablero es una pantalla un
poco inclinada hacia ti.

## Qué ves

| Zona | Qué es |
| --- | --- |
| Panel izquierdo (un tercio) | El título, el estado de la partida, el rival y el color. |
| Escenario (dos tercios) | El rival al fondo, el tablero inclinado delante y los marcadores a los lados de su cabeza. |

## Las decisiones, una por una

### 1. El escenario ocupa dos tercios de la pantalla

La partida es lo único importante de esta pestaña, así que se queda con casi todo el espacio. La
columna del escenario vale `2fr` y la del panel `1fr` (mínimo 260 px). El escenario mide casi todo
el alto de la ventana para que el tablero entero se vea sin hacer scroll.

### 2. El tablero es una pantalla inclinada 18°

Se inclina con `rotateX(18deg)` y una perspectiva suave. El borde de atrás se ve algo más pequeño y
el de delante, a tamaño completo, igual que una pantalla apoyada en una mesa. **Solo 18°** porque
más ángulo estrecha demasiado las casillas del fondo y cuesta pulsarlas. Las casillas siguen siendo
botones normales: el navegador calcula bien dónde pinchas aunque estén inclinadas. Encima lleva un
brillo muy tenue, como de cristal.

### 3. El rival está sentado al otro lado

El personaje está arriba, en el centro, y una **mesa** lo tapa de la cintura para abajo. Eso hace
tres cosas a la vez: da profundidad (el tablero queda delante de él), deja a la vista justo lo que
expresa (la cara) y evita dibujar el cuerpo entero.

### 4. El escenario es oscuro en los dos temas

Es una escena con su propia luz, no un trozo de la página. Así el tablero verde y el personaje se
ven igual de bien con el tema claro o el oscuro y solo hay que dibujar a cada personaje una vez. El
panel de la izquierda sí sigue el tema de la web.

### 5. El avatar reacciona a la partida

Cada estado del juego tiene su gesto:

| Lo que pasa | Lo que hace el personaje |
| --- | --- |
| Empieza la partida | Saluda con un saltito y una frase. |
| Piensa el bot | Ladea la cabeza, levanta una ceja y aparecen tres puntos. |
| Mueve el bot | **Estira un brazo hasta la casilla** y suelta la ficha. Después hace un saltito. |
| Haces una jugada grande (4 fichas o más) | Se sorprende y dice una frase. |
| El bot hace una jugada grande | Sonríe con destellos. |
| Alguien pasa | Lo comenta. |
| Gana el bot | Salta de alegría. |
| Gana la persona | Se pone triste, con lágrimas. |

También **sigue el puntero con los ojos** mientras lo mueves por el escenario (solo con ratón).

### 6. El brazo estirado

Es lo que hace que parezca que el bot juega de verdad: la ficha sale de su hombro y viaja hasta la
casilla elegida. Se dibuja como una barra girada hacia el destino y estirada con `scaleX`; la mano
viaja por el mismo camino y a la misma vez. Dura **300 ms** al salir y **240 ms** al volver, porque
ocurre decenas de veces por partida y no puede hacer esperar. Solo anima `transform`.

### 7. Los movimientos tranquilos y los vistosos

- **Siempre en marcha, muy suave:** respirar, mecerse, parpadear. Son CSS puro, así que no se
  entrecortan mientras Python arranca.
- **Solo en momentos puntuales:** el saltito, los destellos y las lágrimas. Un personaje que se
  menea todo el rato distrae a quien juega.
- **Con «reducir movimiento» activado** el brazo no se estira y el personaje solo cambia de cara.

### 8. Los marcadores van a los lados de la cabeza

Negras a la izquierda y blancas a la derecha, con el emoji del jugador en grande y una ficha del
color que lleva. El turno se marca con un aro. Los puntitos de «pensando» ya no están en el
marcador: los muestra el bocadillo.

### 9. El bocadillo y el estado dicen lo mismo, cada uno a su manera

El **estado** (en el panel) es claro y sirve a lectores de pantalla: «Te toca». El **bocadillo** lo
dice con gracia: «Elige bien, que yo no me dejo». El bocadillo es decorativo y no se lee en voz
alta, para no repetirlo.

### 10. En el móvil todo se apila

El escenario sube arriba (el tablero es lo primero) y el panel queda debajo; antes de empezar es al
revés, para elegir rival. Los marcadores se reducen a icono y número y el bocadillo pasa a ser una
tira de una línea sobre las coordenadas, para no tapar ninguna casilla.

### 11. Las medidas salen del escenario, no de la pantalla

El tamaño del tablero y del avatar usa unidades `cqw` y `cqh` (un porcentaje del propio
escenario). Así los dos se reparten el alto sin una media query por cada tamaño de ventana.

## Cómo añadir otro personaje

1. Dibuja el personaje en un SVG de `viewBox="0 0 400 480"` con las mismas clases que Mr. 2
   (`av__body`, `av__head`, las bocas `m-closed`, `m-grin`, `m-o` y `m-sad`, etc.). La lista completa
   está en `web/js/avatars.js`.
2. Regístralo con `RB.avatars.register({ id, name, spot, shoulder, head, svg, lines })`.
3. Cambia `forBot()` para que cada bot use el suyo.

Los estados de ánimo y las animaciones son comunes (`web/css/avatar.css`), así que un personaje
nuevo reacciona al juego sin escribir nada más.

## Dónde está cada cosa

| Archivo | Qué contiene |
| --- | --- |
| `web/css/jugar.css` | La disposición, el escenario, el tablero inclinado y los marcadores. |
| `web/css/avatar.css` | Los bucles, las caras y el brazo estirado. |
| `web/js/avatars.js` | El dibujo de Mr. 2 y sus frases. |
| `web/js/stage.js` | Lo que hace el personaje: ánimo, bocadillo, ojos y brazo. |
| `web/js/play.js` | La partida; avisa al escenario de lo que pasa. |
| `tests/test_web_jugar.py` | Comprueba que HTML, CSS y JS cuadran entre sí. |
