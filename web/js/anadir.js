/* La página «Añade tu bot»: colorea los bloques de código y los copia con un botón.
 *
 * El código está en el HTML como texto normal (se lee sin JavaScript y los tests lo extraen y lo
 * ejecutan de verdad); aquí solo se le pone color. Nada se escribe con innerHTML: cada trozo es un
 * nodo de texto, así que el código no puede inyectar nada.
 */
(function () {
  "use strict";

  const RB = window.RB;

  /* Cada lenguaje es una expresión con un grupo por clase de color, en este orden. */
  const GRAMMARS = {
    python: {
      re: /(#.*$)|("""[\s\S]*?""")|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')|(\b(?:import|from|class|def|return|if|else|for|in|not|and|or|None|True|False)\b)|(@\w+)/gm,
      classes: ["com", "str", "str", "kw", "dec"],
    },
    yaml: {
      re: /(#.*$)|("[^"\n]*")|(^\s*-?\s*[A-Za-z_][\w-]*(?=:))/gm,
      classes: ["com", "str", "kw"],
    },
    bash: {
      re: /(#.*$)|("[^"\n]*")|(^(?:git|python|pip|pytest|ruff|cd)\b)/gm,
      classes: ["com", "str", "kw"],
    },
  };

  function paint(code, grammar) {
    const text = code.textContent;
    const fragments = document.createDocumentFragment();
    let last = 0;
    grammar.re.lastIndex = 0;
    for (let match = grammar.re.exec(text); match; match = grammar.re.exec(text)) {
      if (match.index > last) fragments.append(text.slice(last, match.index));
      const group = match.findIndex((value, i) => i > 0 && value !== undefined) - 1;
      const span = document.createElement("span");
      span.className = "tok tok--" + grammar.classes[group];
      span.textContent = match[0];
      fragments.append(span);
      last = match.index + match[0].length;
      if (match[0] === "") grammar.re.lastIndex += 1;
    }
    if (last < text.length) fragments.append(text.slice(last));
    code.replaceChildren(fragments);
  }

  function copy(button, code) {
    const original = button.textContent;
    const done = (text) => {
      button.textContent = text;
      button.dataset.state = text === "Copiado" ? "ok" : "error";
      setTimeout(() => { button.textContent = original; delete button.dataset.state; }, 1600);
    };
    if (!navigator.clipboard) return done("No se pudo");
    navigator.clipboard.writeText(code.textContent).then(() => done("Copiado"), () => done("No se pudo"));
  }

  function init() {
    document.querySelectorAll(".code").forEach((block) => {
      const code = block.querySelector("code");
      const grammar = GRAMMARS[block.dataset.lang];
      if (grammar) paint(code, grammar);
      block.querySelector(".code__copy").addEventListener("click", (event) => copy(event.currentTarget, code));
    });
  }

  RB.views = RB.views || {};
  RB.views.anadir = { init: init };
})();
