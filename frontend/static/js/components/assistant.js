// Panel del asistente: solo se abre y se cierra. No tiene funcionalidad todavía (docs/diseno.md).
const panel = document.getElementById("assistant-panel");
const toggle = document.querySelector("[data-assistant-toggle]");
const closer = document.querySelector("[data-assistant-close]");

function show(open, { focus = false } = {}) {
  panel.hidden = !open;
  toggle.classList.toggle("is-active", open);
  toggle.setAttribute("aria-expanded", String(open));
  toggle.setAttribute("aria-label", open ? "Ocultar asistente" : "Abrir asistente");
  if (focus) toggle.focus();
}

if (panel && toggle && closer) {
  toggle.addEventListener("click", () => show(panel.hidden));
  closer.addEventListener("click", () => show(false, { focus: true }));
}
