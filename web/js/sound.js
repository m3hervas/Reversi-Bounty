/* El sonido: efectos sintetizados con Web Audio, sin descargar ningún archivo.
 *
 *   RB.sound.play("move", { flips: 3 })   poner ficha y girar tres
 *   RB.sound.play("pass" | "win" | "lose" | "draw")
 *   RB.sound.enabled()                    ¿está activado?
 *   RB.sound.toggle()                     lo activa o desactiva y lo recuerda
 *
 * Reglas de la casa:
 *   - Nada suena hasta que la persona hace algo (los navegadores no dejan crear audio antes
 *     de un gesto), y el volumen es bajo: es un acompañamiento, no un protagonista.
 *   - El botón de la cabecera lo apaga del todo. La elección se guarda en el navegador.
 *   - Si el navegador no tiene Web Audio o falla, no pasa nada: el juego sigue en silencio.
 *   - Los golpes de las fichas siguen el ritmo de la animación: la nueva cae y las volteadas
 *     giran una tras otra, con los mismos retrasos que board.css.
 */
(function () {
  "use strict";

  const RB = (window.RB = window.RB || {});
  const STORE = "rb-sonido";
  const MASTER_GAIN = 0.55;
  const FLIP_BASE_S = 0.09;  // igual que FLIP_BASE_MS de board.js
  const FLIP_STEP_S = 0.055; // igual que FLIP_STEP_MS de board.js
  const MAX_TICKS = 7;       // más giros no se distinguen: suenan como una cascada

  let ctx = null;
  let master = null;
  let noise = null;
  let on = readPreference();

  function readPreference() {
    try { return localStorage.getItem(STORE) !== "off"; } catch (e) { return true; }
  }

  function savePreference() {
    try { localStorage.setItem(STORE, on ? "on" : "off"); } catch (e) { /* no se recordará */ }
  }

  /* El contexto se crea la primera vez que hace falta, ya dentro de un gesto de la persona. */
  function audio() {
    if (!ctx) {
      const Context = window.AudioContext || window.webkitAudioContext;
      if (!Context) return null;
      ctx = new Context();
      master = ctx.createGain();
      master.gain.value = MASTER_GAIN;
      master.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  /* Un segundo de ruido blanco, reutilizable: es la «madera» de cada golpe. */
  function noiseBuffer() {
    if (!noise) {
      noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
      const data = noise.getChannelData(0);
      for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    }
    return noise;
  }

  /* Una nota con ataque corto y caída exponencial (suena a algo que se golpea, no a un pitido). */
  function tone(at, freq, length, peak, type, glideTo) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type || "sine";
    osc.frequency.setValueAtTime(freq, at);
    if (glideTo) osc.frequency.exponentialRampToValueAtTime(glideTo, at + length);
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(peak, at + 0.006);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + length);
    osc.connect(gain).connect(master);
    osc.start(at);
    osc.stop(at + length + 0.02);
  }

  /* Un chasquido de ruido filtrado: da el cuerpo seco del golpe de una ficha. */
  function knock(at, centre, length, peak) {
    const src = ctx.createBufferSource();
    src.buffer = noiseBuffer();
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = centre;
    filter.Q.value = 1.3;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(peak, at);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + length);
    src.connect(filter).connect(gain).connect(master);
    src.start(at, Math.random() * 0.5);
    src.stop(at + length + 0.02);
  }

  const cues = {
    /* La ficha nueva cae (golpe grave y seco) y cada ficha volteada hace un «tic» más agudo. */
    move(now, opts) {
      knock(now, 900, 0.07, 0.5);
      tone(now, 190, 0.12, 0.34, "sine", 95);
      const flips = Math.min(opts && opts.flips ? opts.flips : 0, MAX_TICKS);
      for (let i = 0; i < flips; i++) {
        const at = now + FLIP_BASE_S + i * FLIP_STEP_S;
        knock(at, 2300 + i * 90, 0.045, 0.22);
        tone(at, 540 + i * 24, 0.07, 0.07, "triangle", 420);
      }
    },
    pass(now) {
      tone(now, 392, 0.16, 0.16, "triangle");
      tone(now + 0.13, 294, 0.24, 0.16, "triangle");
    },
    win(now) {
      [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => tone(now + i * 0.1, f, 0.34, 0.15, "triangle"));
    },
    lose(now) {
      [392, 329.63, 261.63].forEach((f, i) => tone(now + i * 0.16, f, 0.4, 0.15, "triangle"));
    },
    draw(now) {
      tone(now, 440, 0.22, 0.14, "triangle");
      tone(now + 0.2, 440, 0.34, 0.14, "triangle");
    },
  };

  function play(kind, opts) {
    if (!on || !cues[kind]) return;
    try {
      if (!audio()) return;
      cues[kind](ctx.currentTime + 0.005, opts);
    } catch (err) {
      /* El sonido es un extra: un fallo aquí nunca debe afectar a la partida. */
    }
  }

  // ------------------------------------------------------- botón de la cabecera --- //

  function paintButton() {
    const btn = document.getElementById("sound-btn");
    if (!btn) return;
    btn.setAttribute("aria-pressed", String(on));
    btn.setAttribute("aria-label", on ? "Silenciar los sonidos" : "Activar los sonidos");
    btn.dataset.on = String(on);
  }

  function toggle() {
    on = !on;
    savePreference();
    paintButton();
    if (on) play("move", { flips: 2 }); // al activarlo suena un golpe suave: así se sabe que funciona
    return on;
  }

  function init() {
    const btn = document.getElementById("sound-btn");
    if (btn) btn.addEventListener("click", toggle);
    paintButton();
  }

  RB.sound = { play: play, toggle: toggle, enabled: () => on, init: init };
})();
