/* Los avatares: el personaje que está sentado al otro lado del tablero.
 *
 * Un avatar es solo un dibujo y unas frases. No sabe nada del juego: el escenario (stage.js) lo
 * mueve y lo hace reaccionar. Para añadir otro personaje basta con llamar a
 * RB.avatars.register({...}) con estos campos y dibujarlo con el mismo esqueleto de clases:
 *
 *   id        texto corto y único ("mr2")
 *   name      cómo se llama en pantalla ("Mr. 2")
 *   spot      color del foco de luz que tiene detrás
 *   shoulder  [x, y] del hombro del que sale el brazo, en el viewBox del dibujo
 *   head      [x, y] del centro de la cabeza (hacia donde mira hay que apuntar los ojos)
 *   svg       el dibujo (viewBox 0 0 400 480) con estas clases, que son las que animan los estilos:
 *               .av__body    el cuerpo entero (respira)
 *               .av__head    la cabeza, con el cuello como eje
 *               .av__iris    cada pupila (siguen al puntero)
 *               .av__eyes / .av__eyes-happy / .av__lids / .av__brow--l / .av__brow--r
 *               .m-closed / .m-grin / .m-o / .m-sad       las bocas, una por estado de ánimo
 *               .av__spark / .av__tear                    destellos y lágrimas
 *   lines     frases por situación: hello, think, move, bigMove, yourBigMove, pass, youPass,
 *             win, lose, draw, forfeit. Cada una es una lista; se elige una al azar.
 *
 * Los estados de ánimo (neutral, think, happy, surprised, sad) se dibujan en avatar.css.
 * Qué avatar sale en cada partida lo decide forBot(): de momento, Mr. 2 para todos los bots.
 */
(function () {
  "use strict";

  const RB = (window.RB = window.RB || {});
  const registry = {};

  /* Mr. 2: un bailarín exagerado, de pelo rizado enorme, pestañas kilométricas y mucho colorete.
   * Dibujo propio y sencillo, hecho solo con formas de SVG (sin imágenes externas). */
  const MR2_SVG = `
<svg class="av" viewBox="0 0 400 480" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false" data-mood="neutral">
  <defs>
    <linearGradient id="av-skin" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fdf6fa"/><stop offset="1" stop-color="#eddcf1"/>
    </linearGradient>
    <radialGradient id="av-hair" cx="50%" cy="30%" r="75%">
      <stop offset="0" stop-color="#6a72e6"/><stop offset="0.55" stop-color="#3b41b0"/><stop offset="1" stop-color="#232774"/>
    </radialGradient>
    <linearGradient id="av-suit" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#d9d5f1"/>
    </linearGradient>
    <linearGradient id="av-lips" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f23a74"/><stop offset="1" stop-color="#c8174f"/>
    </linearGradient>
  </defs>

  <g class="av__body">
    <!-- brazos (en reposo; cuando mueve ficha, el brazo que se estira lo dibuja el escenario) -->
    <g class="av__arm av__arm--l">
      <path d="M112 318 Q66 366 72 438" fill="none" stroke="#c9c4ea" stroke-width="40" stroke-linecap="round"/>
      <path d="M112 318 Q66 366 72 438" fill="none" stroke="#f3f1fc" stroke-width="34" stroke-linecap="round"/>
      <circle cx="72" cy="450" r="25" fill="#fff" stroke="#ff7ac8" stroke-width="6"/>
    </g>
    <g class="av__arm av__arm--r">
      <path d="M288 318 Q334 366 328 438" fill="none" stroke="#c9c4ea" stroke-width="40" stroke-linecap="round"/>
      <path d="M288 318 Q334 366 328 438" fill="none" stroke="#f3f1fc" stroke-width="34" stroke-linecap="round"/>
      <circle cx="328" cy="450" r="25" fill="#fff" stroke="#ff7ac8" stroke-width="6"/>
    </g>
    <!-- cuello y torso -->
    <rect x="174" y="252" width="52" height="60" rx="18" fill="#e6d3ea"/>
    <path d="M84 480 L96 346 Q100 304 142 292 L258 292 Q300 304 304 346 L316 480 Z" fill="url(#av-suit)"/>
    <!-- el escudo del pecho: un cisne muy simplificado -->
    <circle cx="200" cy="392" r="30" fill="#7a86ee"/>
    <path d="M184 402 C198 410 216 406 220 392 C223 382 216 376 209 379 C203 382 205 389 210 388" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
    <!-- golilla -->
    <g fill="#fff" stroke="#c9c4ea" stroke-width="2.5">
      <circle cx="140" cy="306" r="21"/><circle cx="170" cy="316" r="21"/><circle cx="200" cy="320" r="21"/>
      <circle cx="230" cy="316" r="21"/><circle cx="260" cy="306" r="21"/>
    </g>
  </g>

  <g class="av__head">
    <!-- pelo de atrás: un moño rizado enorme -->
    <g class="av__hair-back" fill="url(#av-hair)">
      <ellipse cx="200" cy="160" rx="120" ry="104"/>
      <circle cx="104" cy="196" r="36"/><circle cx="296" cy="196" r="36"/>
      <circle cx="86" cy="240" r="28"/><circle cx="314" cy="240" r="28"/>
      <circle cx="200" cy="64" r="46"/><circle cx="148" cy="80" r="42"/><circle cx="252" cy="80" r="42"/>
      <circle cx="106" cy="116" r="38"/><circle cx="294" cy="116" r="38"/>
      <circle cx="174" cy="46" r="36"/><circle cx="226" cy="46" r="36"/>
    </g>
    <path d="M168 44 Q200 20 240 48" fill="none" stroke="#ff7ac8" stroke-width="10" stroke-linecap="round"/>

    <!-- cara -->
    <path d="M138 198 Q138 134 200 134 Q262 134 262 198 L262 222 Q262 284 200 292 Q138 284 138 222 Z" fill="url(#av-skin)"/>
    <ellipse cx="150" cy="244" rx="17" ry="10" fill="#ff8fb8" opacity="0.55"/>
    <ellipse cx="250" cy="244" rx="17" ry="10" fill="#ff8fb8" opacity="0.55"/>
    <!-- sombra de ojos azul -->
    <path d="M142 198 Q166 166 192 196 Q166 184 142 198Z" fill="#4fc3dc"/>
    <path d="M258 198 Q234 166 208 196 Q234 184 258 198Z" fill="#4fc3dc"/>

    <!-- ojos abiertos -->
    <g class="av__eyes">
      <ellipse cx="166" cy="204" rx="18" ry="13" fill="#fff"/>
      <ellipse cx="234" cy="204" rx="18" ry="13" fill="#fff"/>
      <g class="av__iris"><circle cx="166" cy="204" r="8.5" fill="#241c4a"/><circle cx="169.5" cy="200.5" r="2.8" fill="#fff"/></g>
      <g class="av__iris"><circle cx="234" cy="204" r="8.5" fill="#241c4a"/><circle cx="237.5" cy="200.5" r="2.8" fill="#fff"/></g>
      <path d="M146 200 Q166 180 188 200" fill="none" stroke="#1b1540" stroke-width="4.5" stroke-linecap="round"/>
      <path d="M254 200 Q234 180 212 200" fill="none" stroke="#1b1540" stroke-width="4.5" stroke-linecap="round"/>
      <path d="M148 197 L139 190 M154 190 L147 181 M186 194 L192 186" fill="none" stroke="#1b1540" stroke-width="3.5" stroke-linecap="round"/>
      <path d="M252 197 L261 190 M246 190 L253 181 M214 194 L208 186" fill="none" stroke="#1b1540" stroke-width="3.5" stroke-linecap="round"/>
    </g>
    <!-- ojos contentos: arcos -->
    <g class="av__eyes-happy" fill="none" stroke="#1b1540" stroke-width="5" stroke-linecap="round">
      <path d="M148 208 Q166 186 186 208"/><path d="M252 208 Q234 186 214 208"/>
      <path d="M149 200 L140 194 M185 200 L192 194 M251 200 L260 194 M215 200 L208 194" stroke-width="3.5"/>
    </g>
    <!-- párpados: bajan un instante para parpadear -->
    <g class="av__lids" fill="url(#av-skin)">
      <ellipse cx="166" cy="204" rx="20" ry="15"/><ellipse cx="234" cy="204" rx="20" ry="15"/>
    </g>
    <!-- lágrimas (solo cuando está triste) -->
    <path class="av__tear" d="M150 222 Q144 236 150 242 Q156 236 150 222Z" fill="#8fd9ff"/>
    <path class="av__tear av__tear--r" d="M250 222 Q244 236 250 242 Q256 236 250 222Z" fill="#8fd9ff"/>

    <!-- cejas -->
    <path class="av__brow av__brow--l" d="M144 170 Q166 148 194 162" fill="none" stroke="#241c4a" stroke-width="4.5" stroke-linecap="round"/>
    <path class="av__brow av__brow--r" d="M256 170 Q234 148 206 162" fill="none" stroke="#241c4a" stroke-width="4.5" stroke-linecap="round"/>
    <!-- nariz -->
    <path d="M200 216 Q195 236 204 240" fill="none" stroke="#cfaed2" stroke-width="3.5" stroke-linecap="round"/>

    <!-- bocas: una por estado de ánimo -->
    <g class="av__mouth">
      <path class="m-closed" d="M176 258 Q189 249 200 255 Q211 249 224 258 Q212 273 200 274 Q188 273 176 258Z" fill="url(#av-lips)"/>
      <g class="m-grin">
        <path d="M170 254 Q200 292 230 254 Q200 262 170 254Z" fill="#8f1238"/>
        <path d="M178 256 Q200 270 222 256 Q200 261 178 256Z" fill="#fff"/>
        <path d="M170 254 Q200 292 230 254" fill="none" stroke="#f23a74" stroke-width="4" stroke-linecap="round"/>
      </g>
      <ellipse class="m-o" cx="200" cy="264" rx="11" ry="14" fill="#8f1238" stroke="#f23a74" stroke-width="4.5"/>
      <path class="m-sad" d="M178 272 Q200 252 222 272" fill="none" stroke="#e0245e" stroke-width="6" stroke-linecap="round"/>
    </g>

    <!-- flequillo y rizos de delante -->
    <g fill="url(#av-hair)">
      <path d="M134 190 Q128 124 200 116 Q272 124 266 190 Q252 150 200 148 Q148 150 134 190Z"/>
      <circle cx="150" cy="150" r="20"/><circle cx="250" cy="150" r="20"/><circle cx="200" cy="130" r="22"/>
    </g>
    <path d="M178 118 Q200 108 224 120" fill="none" stroke="#ff7ac8" stroke-width="7" stroke-linecap="round"/>

    <!-- destellos (cuando está contento) -->
    <g class="av__spark" fill="#ffe27a">
      <path d="M62 96 l6 16 16 6 -16 6 -6 16 -6 -16 -16 -6 16 -6z"/>
      <path d="M338 72 l5 13 13 5 -13 5 -5 13 -5 -13 -13 -5 13 -5z"/>
      <path d="M52 214 l4 10 10 4 -10 4 -4 10 -4 -10 -10 -4 10 -4z"/>
      <path d="M350 206 l4 10 10 4 -10 4 -4 10 -4 -10 -10 -4 10 -4z"/>
    </g>
  </g>
</svg>`;

  const MR2 = {
    id: "mr2",
    name: "Mr. 2",
    spot: "rgba(255, 122, 200, 0.26)",
    shoulder: [296, 326],
    head: [200, 210],
    svg: MR2_SVG,
    lines: {
      hello: ["¡Que empiece el espectáculo!", "¿Jugamos, cariño?", "Elige bien, que yo no me dejo."],
      think: ["Mmm… déjame pensar…", "Un momentito, cariño…", "Qué difícil, qué difícil…"],
      move: ["¡Ahí va esa!", "Toma, toma, toma.", "Mi jugada, con mucho estilo."],
      bigMove: ["¡Bravo! ¡Qué jugada!", "¡Te las he dado la vuelta todas!", "¡Y con elegancia!"],
      yourBigMove: ["¡Ay! ¡Eso ha dolido!", "¡Qué barbaridad!", "¡Vaya! No me lo esperaba."],
      pass: ["No tengo jugada… ¡paso!", "Me toca pasar. ¡Qué drama!"],
      youPass: ["Tú no puedes mover. ¡Sigo yo!", "Sin jugada para ti. ¡Otra vez yo!"],
      win: ["¡Bravo, bravo! ¡He ganado!", "¡Qué espectáculo! ¡Gané!"],
      lose: ["¡Me has ganado! ¡Qué fuerte!", "Buah… ¡qué bien juegas!"],
      draw: ["¡Empate! Qué elegancia.", "Ni para ti ni para mí."],
      forfeit: ["¡Ay! Me he equivocado de jugada…"],
    },
  };

  RB.avatars = {
    register(avatar) { registry[avatar.id] = avatar; },
    get(id) { return registry[id] || null; },
    /* De momento todos los bots tienen la cara de Mr. 2. Más adelante cada bot podrá traer la suya. */
    forBot() { return registry.mr2; },
    list() { return Object.keys(registry); },
  };
  RB.avatars.register(MR2);
})();
