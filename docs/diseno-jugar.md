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
| Rivales | `#/bots` | Un cartel por cada bot admitido en el registro, de cuatro en cuatro. Los de otros equipos dicen al pie de qué tripulación vienen. |
| Marcador | `#/marcador` | La clasificación del torneo nocturno: el podio con los tres primeros, la tabla completa (% de victorias, fichas, infracciones y qué bots son de fuera), y el **cara a cara** de todos contra todos. Ver [dónde se publica la clasificación](referencia/torneo.md#donde-se-publica-la-clasificacion). |
| Leyes del mar | `#/reglas` | Las cuatro reglas con un ejemplo cada una, un mapa de las casillas y cinco consejos. |
| Añade tu Bot | `#/anadir` | El código de ejemplo a la izquierda y los cuatro pasos a la derecha. |

## Las decisiones, una por una

### 1. Una web estática, y las reglas son de Python

Ninguna regla del Reversi está en JavaScript. Las jugadas legales, los volteos, los pasos, el final y los
bots salen del paquete `reversibounty`, que `web/py.zip` lleva al navegador. El JavaScript pregunta al
puente (`web/webglue.py`) y dibuja. Un test comprueba que cada función que llama la web existe en el
puente y que en el JS no hay reglas del juego.

Por eso las jugadas legales también se pueden pedir desde la consola del navegador (F12), sin pasar
por el tablero:

```js
const v = await RB.engine.call("new_game", []);
await RB.engine.call("legal_moves", [v.state]);   // [[2, 3], [3, 2], [4, 5], [5, 4]]
```

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

Cuando juegan dos bots, en su lugar sale **Parar**: la partida se detiene antes de la siguiente jugada y **Seguir** la reanuda.

Con una persona en la mesa, debajo está **Deshacer** (también con Ctrl+Z). Cada vez que le toca a una persona, la web guarda la
posición que le dio el motor; deshacer vuelve a la anterior, así que contra un bot quita tu jugada y su
respuesta. No se salta ninguna regla: solo se vuelve a posiciones que el motor ya dio por buenas. Para
que no sirva de trampa, una partida contra un bot no se puede deshacer una vez cobrada la recompensa.

Todos los carteles (Rivales, Lucha, Marcador, la portada y el tutorial) son la misma pieza con estilo
de cartel impreso: papel envejecido con su clavo, «SE BUSCA» a todo el ancho, la foto vertical con un
filo oscuro para que el personaje salga **siempre de cuerpo entero**, el nombre tan grande como quepa en
una línea y la recompensa con el símbolo del berry. Todo escala con el ancho del cartel, así que se ve
igual en grande y en pequeño.

### 4. Quién envió cada bot

Un bot es una clase de Python, no una persona: lo que importa es cómo juega. Por eso la partida y el
marcador no enseñan autores. En Rivales, debajo de cada cartel, pone de qué tripulación es: los
**bots de otros equipos** llevan «Tripulación de:» y los autores que declara la clase, como
agradecimiento; los nuestros, «Tripulación de: Reversi Bounty». La web
sabe que un bot es de fuera porque no vive dentro del paquete (`reversibounty.bots`) sino en
`players/custom/`. Un test vigila que los autores no salgan en ningún otro sitio.

### 5. Los personajes son decoración, no datos

El alias, las frases y el precio de cada rival están en `web/js/crew.js` y las imágenes en `web/img/`. El
motor no sabe nada de ellos. Un bot nuevo sin personaje recibe un cartel genérico con su emoji y un
precio calculado a partir de su nombre, así que **añadir un bot nunca rompe la web**.

| Rival | Personaje | Alias |
| --- | --- | --- |
| Buggy aleatorio | Buggy | Payaso Suertudo |
| Wapol voraz | Wapol | El Rey Glotón |
| Zeff minimax | Zeff | Pierna Roja |
| Nami navegante | Nami | La Gata Ladrona |
| Kraken alfa-beta | Kraken | Terror Abisal |
| Car_lu | Karoo | Pato Relámpago |
| Minimax de Zena | Mr. 5 | El Hombre Bomba |
| Brook silencioso | Brook | El Rey del Soul |

Cada personaje juega además con **sus propias fichas**: el fondo dice el bando (dorado para los
sombreros, oscuro para las calaveras) y el dibujo, quién juega. Buggy lleva su nariz de payaso, Wapol
su corona, Zeff su gorro de cocinero, Nami una mandarina, el Kraken un tentáculo sobre dos sables, Karoo su cabeza de pato con casco, Mr. 5 su chapa del 5 sobre una explosión y Brook su violín. Son SVG propios en `web/img/fichas/`; una
persona o un bot sin personaje juega con las fichas de siempre.

Las imágenes de los personajes se hicieron con IA para este trabajo y están dentro de `web/img/`, con
fondo transparente (los tests comprueban que tienen canal alfa).

### 6. Cada rival vale lo que juega

La recompensa de cada bot no es al azar: sigue su fuerza en el torneo. Se calcula como
**5 M + 190 M × p^1,5**, donde *p* es la fracción de puntos que consiguió en el torneo nocturno. La
curva sube despacio abajo y deprisa arriba, así que ganar a un bot fuerte vale mucho más que ganar a
uno flojo. Un bot recién llegado lleva un valor provisional hasta su primer torneo.

| Rival | % de puntos | Recompensa |
| --- | --- | --- |
| Kraken alfa-beta | 82,5 % | 147 M |
| Car_lu | 80 % (30 partidas medidas aparte) | 141 M |
| Zeff minimax | 72,5 % | 122 M |
| Nami navegante | 70 % | 116 M |
| Minimax de Zena | provisional | 110 M |
| Brook silencioso | provisional | 60 M |
| Wapol voraz | 22,5 % | 25 M |
| Buggy aleatorio | 2,5 % | 6 M |

### 7. Tu recompensa es solo un juego

Cada victoria contra un bot sube tu recompensa: más cuanto más temible es el rival. Se guarda en el
navegador (`localStorage`) y sirve para divertirse; **no son los puntos del torneo**. Los rangos van de
*Grumete* a *Emperador del Reversi*.

### 8. La barra de arriba

La barra es el *Log Pose* de la web: cada apartado lleva su icono, el activo se marca en dorado y tu
recompensa está siempre a la vista (lleva a tu cartel en la portada). Al bajar por la página se
compacta y echa sombra, y el borde es una cuerda trenzada en vez de una raya.

### 9. Día y noche

El tema claro es un día soleado en el mar y el oscuro, la misma isla de noche. Los colores son variables
de `web/css/theme.css`, que se redefinen para el modo oscuro del sistema y para la elección a mano.

### 10. Accesibilidad

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
| La clasificación del torneo | `web/js/marcador.js` |
| La conexión con Python (Pyodide) | `web/js/engine.js` y `web/js/worker.js` |
| Un personaje | `web/img/` y su entrada en `web/js/crew.js` |

## Limitaciones

- La web necesita conexión la primera vez: Pyodide se descarga de un CDN.
- No se ha probado con lector de pantalla ni en Safari.
- Un bot que tarde más de 20 s pierde la partida y se reinicia el motor.
