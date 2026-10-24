/* La tripulación: la personalidad de cada rival y el sistema de recompensas.
 *
 * Todo esto es decoración: el motor de Python no sabe nada de ello. Los rivales salen del
 * registro (nombre, emoji, autores, descripción); aquí solo se les pone alias, frases y un
 * precio por la cabeza. Un bot nuevo, sin entrada aquí, recibe un cartel genérico con un
 * precio sacado de su nombre, así que añadir un bot nunca rompe la web.
 *
 *   RB.crew.persona(bot)          { aka, bounty, lines }
 *   RB.crew.line(bot, evento)     una frase para: hello | think | big | move | win | lose | draw | forfeit
 *   RB.crew.profile               { name, berries, w, d, l }  (se guarda en localStorage)
 *   RB.crew.reward(bot, ...)      berries que da una victoria
 *   RB.crew.rank(berries)         { title, next, nextAt, pct }
 */
(function () {
  "use strict";

  const RB = (window.RB = window.RB || {});
  const KEY = "bb-recompensa";

  const PERSONAS = {
    "Mr. 2 aleatorio": {
      aka: "El Payaso Afortunado", bounty: 15000000, img: "img/mr2.png", accent: "#ff4fa3",
      lines: {
        hello: ["¡Soy el magnífico capitán! Jugaré… a lo que salga.", "¡Que se prepare el mar, que voy a hacer una jugada!"],
        think: ["Mmm… ¡esta! ¡O esta! ¡Da igual!", "Cierro los ojos y… ¡ahí va!"],
        big: ["¡¿Quién te ha enseñado eso?!", "¡Eso no estaba en mi plan! (no tengo plan)"],
        move: ["¡Pura suerte genial!", "¡Lo hice a propósito, lo juro!", "¡Bum! ¡Casualidad con estilo!"],
        win: ["¡Gané! ¡Era mi plan desde el principio!"], lose: ["¡Esto no cuenta, me han empujado!"],
        draw: ["¡Empate! ¡Eso es que soy invencible a medias!"], forfeit: ["¡Era una jugada secreta!"],
      },
    },
    "Wapol voraz": {
      aka: "El Tragón del Botín", bounty: 28000000, img: "img/wapol.png", accent: "#ff8a1f",
      lines: {
        hello: ["Todas las fichas serán mías. ¡Todas!", "Cada ficha que voltee es una moneda más."],
        think: ["¿Cuál me da más? … ¡Esa!", "Contando botín…"],
        big: ["¡Ladrón! Esas eran mías.", "¡Eso me ha dolido en la cartera!"],
        move: ["¡Más, más fichas!", "Mmm, qué buen botín.", "Hoy ceno fichas."],
        win: ["El botín es mío. Siempre lo fue."], lose: ["Me faltó plan, no hambre…"],
        draw: ["¿Empate? Qué escasez más cruel."], forfeit: ["¡Me pasé de listo!"],
      },
    },
    "Zeff minimax": {
      aka: "El Cocinero Estratega", bounty: 150000000, img: "img/zeff.png", accent: "#3f86d9",
      lines: {
        hello: ["Siéntate, mocoso. Veamos qué sabes.", "Aquí se cocina a fuego lento y se piensa ocho jugadas."],
        think: ["Calculando ocho jugadas por delante…", "Todo bien sazonado, nada se improvisa."],
        big: ["Hmpf. No está mal, grumete.", "Esa te la apunto."],
        move: ["Cocinado a fuego lento.", "Sin prisa y sin pausa.", "Servido."],
        win: ["Vuelve cuando sepas jugar, mocoso."], lose: ["Jeh. Has ganado. Me gusta tu estilo."],
        draw: ["Empate… respeto."], forfeit: ["Eso no debería pasar en mi cocina."],
      },
    },
  };

  const GENERIC = {
    hello: ["¡Soy nuevo en este mar, pero aprendo rápido!", "¡Que empiece la batalla!"],
    think: ["Pensando mi jugada…", "Déjame mirar el mapa…"],
    big: ["¡Vaya jugada!", "Ouch. Eso ha dolido."],
    move: ["¡Ahí va!", "Una más para mi bandera.", "Veamos qué haces ahora."],
    win: ["¡Victoria para mi tripulación!"], lose: ["Buena partida. ¡Quiero la revancha!"],
    draw: ["Empate. Nadie se hunde hoy."], forfeit: ["¡Ay! Me salté una regla…"],
  };

  /* Un número estable a partir del nombre: el mismo bot siempre vale lo mismo. */
  function hash(text) {
    let n = 7;
    for (const ch of text) n = (n * 31 + ch.codePointAt(0)) % 1000003;
    return n;
  }

  function persona(bot) {
    if (!bot) return { aka: "Rival misterioso", bounty: 0, lines: GENERIC };
    const p = PERSONAS[bot.name];
    if (p) return p;
    return { aka: "Nuevo en el Grand Line", bounty: (5 + (hash(bot.name) % 56)) * 1000000, lines: GENERIC };
  }

  function line(bot, kind) {
    const list = (persona(bot).lines[kind]) || GENERIC[kind] || [""];
    return list[Math.floor(Math.random() * list.length)];
  }

  // ------------------------------------------------------------ recompensas --- //

  const RANKS = [
    { at: 0, title: "Grumete" },
    { at: 5000000, title: "Pirata de agua dulce" },
    { at: 20000000, title: "Pirata temible" },
    { at: 60000000, title: "Supernova" },
    { at: 200000000, title: "Corsario del Grand Line" },
    { at: 600000000, title: "Almirante rebelde" },
    { at: 1500000000, title: "Emperador del Reversi" },
  ];

  function rank(berries) {
    let i = 0;
    RANKS.forEach((r, k) => { if (berries >= r.at) i = k; });
    const next = RANKS[i + 1] || null;
    const pct = next ? Math.round(((berries - RANKS[i].at) / (next.at - RANKS[i].at)) * 100) : 100;
    return { title: RANKS[i].title, next: next && next.title, nextAt: next && next.at, pct: pct };
  }

  function reward(bot, diff, outcome) {
    const base = persona(bot).bounty;
    if (outcome === "win") return Math.round(base / 5 + Math.abs(diff) * 100000);
    if (outcome === "draw") return Math.round(base / 20);
    return 0;
  }

  const fmt = (n) => Number(n).toLocaleString("es-ES");

  // --------------------------------------------------------------- perfil --- //

  function readProfile() {
    try {
      const p = JSON.parse(localStorage.getItem(KEY) || "null");
      if (p && typeof p.berries === "number") return Object.assign({ name: "", w: 0, d: 0, l: 0 }, p);
    } catch (e) { /* sin almacenamiento: se juega igual */ }
    return { name: "", berries: 0, w: 0, d: 0, l: 0 };
  }

  const profile = readProfile();
  function saveProfile() {
    try { localStorage.setItem(KEY, JSON.stringify(profile)); } catch (e) { /* idem */ }
  }

  const LUFFY = { img: "img/luffy.png?v=2", accent: "#e0372e" };

  RB.crew = { LUFFY: LUFFY, persona: persona, line: line, rank: rank, reward: reward, fmt: fmt, profile: profile, save: saveProfile, RANKS: RANKS };
})();
