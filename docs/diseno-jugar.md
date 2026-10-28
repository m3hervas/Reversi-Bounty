# Diseño de la web: Grand Line

Esta página explica **por qué** la web es como es. Cada decisión tiene una razón, y casi todas se
pueden cambiar tocando un número o un archivo. La web sigue la ruta de la
[guía de la asignatura](https://nim-arena.readthedocs.io/en/latest/guide/web-app/static-web/): una
página estática (HTML, CSS y JavaScript, sin servidor ni *build*) que ejecuta en el navegador el mismo
paquete de Python del proyecto con Pyodide, y se publica en GitHub Pages.

## La idea

El Reversi ya es un juego de **dos bandos que se voltean**, y eso encaja con *One Piece*: de un lado
los **sombreros de paja** y del otro las **calaveras**. Voltear una ficha es, literalmente, que cambie de
bandera. Los bots son los rivales del tablón de recompensas y cada uno tiene su cartel de «Se busca».

## Qué ves

| Apartado | Ruta | Qué es |
| --- | --- | --- |
| Portada | `#/` | El título, una moneda que gira entre sombrero y calavera, y **tu cartel de «Se busca»**. |
| Lucha | `#/jugar` | Un cartel a cada lado, el marcador arriba y el tablero en el centro. |
| Rivales | `#/bots` | Un cartel por cada bot admitido en el registro. |
| Leyes del mar | `#/reglas` | Las cuatro reglas con un ejemplo cada una, un mapa de las casillas y cinco consejos. |
| Añade tu Bot | `#/anadir` | El código de ejemplo a la izquierda y los cuatro pasos a la derecha. |

## Las decisiones, una por una

### 1. Una web estática, y las reglas son de Python

Ninguna regla del Reversi está en JavaScript. Las jugadas legales, los volteos, los pasos, el final y los
bots salen del paquete `reversibounty`, que `web/py.zip` lleva al navegador. El JavaScript pregunta al
puente (`web/webglue.py`) y dibuja. Un test comprueba que cada función que llama la web existe en el
puente y que en el JS no hay reglas del juego.

### 2. Las fichas son dos caras de un disco

Cada casilla tiene un disco con la cara del **sombrero de paja** (blancas) y la de la **calavera**
(negras), hechas solo con CSS. Cambiar `data-color` basta para que la ficha gire con una transición:
el JavaScript solo calcula el retardo con el que gira cada ficha según su distancia a la jugada. El
tablero se construye una vez y no se vuelve a dibujar entero.

### 3. Cada bando tiene su cartel

A izquierda y derecha del tablero hay un cartel de «Se busca» por bando. Un bot enseña a su personaje; una
persona enseña a Luffy y su propio nombre y recompensa. Sobre cada cartel está el desplegable que elige
quién juega ese bando, así se puede cambiar de jugadores **en cualquier momento** y poner **dos bots**
a luchar entre ellos. El botón de nueva partida está junto al marcador, que va encima del tablero.

### 4. Los bots son independientes de quien los subió

Los carteles no enseñan los autores. Un bot es una clase de Python, no una persona: lo que importa es
cómo juega. El registro sigue guardando los autores, pero la web no los muestra, y un test lo vigila.

### 5. Los personajes son decoración, no datos

El alias, las frases y el precio de cada rival están en `web/js/crew.js` y las imágenes en `web/img/`. El
motor no sabe nada de ellos. Un bot nuevo sin personaje recibe un cartel genérico con su emoji y un
precio calculado a partir de su nombre, así que **añadir un bot nunca rompe la web**.

| Rival | Personaje | Alias |
| --- | --- | --- |
| Buggy aleatorio | Buggy | El Payaso Afortunado |
| Wapol voraz | Wapol | El Tragón del Botín |
| Zeff minimax | Zeff | El Cocinero Estratega |

Las imágenes de los personajes se hicieron con IA para este trabajo y están dentro de `web/img/`, con
fondo transparente (los tests comprueban que tienen canal alfa).

### 6. Tu recompensa es solo un juego

Cada victoria contra un bot sube tu recompensa: más cuanto más temible es el rival. Se guarda en el
navegador (`localStorage`) y sirve para divertirse; **no son los puntos del torneo**. Los rangos van de
*Grumete* a *Emperador del Reversi*.

### 7. Día y noche

El tema claro es un día soleado en el mar y el oscuro, la misma isla de noche. Los colores son variables
de `web/css/theme.css`, que se redefinen para el modo oscuro del sistema y para la elección a mano.

### 8. Accesibilidad

Hay un enlace para saltar al contenido, el foco se ve, cada casilla tiene un nombre («d3, calavera,
jugada posible») y el tablero se maneja con las flechas y Enter. Con `prefers-reduced-motion` se quitan
las animaciones.

## Qué archivo toca qué

| Quiero cambiar… | Archivo |
| --- | --- |
| Colores, botones, barra superior | `web/css/theme.css` |
| Portada, carteles, reglas, rivales, «Añade tu Bot» | `web/css/pages.css` |
| Tablero, fichas, cartel del rival, marcador | `web/css/play.css` |
| Frases, alias, precios y rangos | `web/js/crew.js` |
| Rutas, tema, sonido, cartel personal | `web/js/app.js` |
| La partida | `web/js/play.js` |
| Un personaje | `web/img/` y su entrada en `web/js/crew.js` |

## Limitaciones

- La web necesita conexión la primera vez: Pyodide se descarga de un CDN.
- No se ha probado con lector de pantalla ni en Safari.
- Un bot que tarde más de 20 s pierde la partida y se reinicia el motor.
