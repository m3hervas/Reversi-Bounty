/* El índice de una página de lectura: una fila de botones que llevan a cada sección.
 *
 *   RB.toc("reglas")     activa el índice de <section data-view="reglas">
 *
 * Los botones llevan a una sección sin tocar la dirección (que ya la usan las rutas), y el índice
 * marca la sección que se está leyendo: la última cuyo borde superior ya ha pasado del tercio
 * superior de la pantalla. La fila se desliza en pantallas estrechas y mantiene a la vista el
 * botón activo.
 */
(function () {
  "use strict";

  const RB = (window.RB = window.RB || {});
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  RB.toc = function (view) {
    const root = document.querySelector('.view[data-view="' + view + '"]');
    if (!root) return;
    const buttons = Array.from(root.querySelectorAll(".toc button"));
    const targets = buttons.map((button) => document.getElementById(button.dataset.scroll));
    const sectionsInOrder = buttons
      .map((button, i) => ({ button: button, target: targets[i] }))
      .filter((item) => item.target)
      .sort((a, b) => (a.target.compareDocumentPosition(b.target) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));

    buttons.forEach((button, i) => {
      button.addEventListener("click", () => {
        if (targets[i]) targets[i].scrollIntoView({ behavior: reduceMotion.matches ? "auto" : "smooth", block: "start" });
      });
    });

    let queued = false;
    function mark() {
      queued = false;
      if (document.documentElement.dataset.view !== view) return;
      const line = window.innerHeight * 0.33;
      let active = null;
      sectionsInOrder.forEach((item) => { if (item.target.getBoundingClientRect().top <= line) active = item.button; });
      buttons.forEach((button) => button.toggleAttribute("aria-current", button === active));
      if (active) {
        const row = active.closest("ol");
        if (row) row.scrollTo({ left: active.offsetLeft - 24, behavior: reduceMotion.matches ? "auto" : "smooth" });
      }
    }
    window.addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(mark); } }, { passive: true });
    mark();
  };
})();
