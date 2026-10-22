// Barra lateral: en escritorio se abre o se cierra (solo íconos); en el celular es un panel que se
// abre desde la marca. No se recuerda entre páginas: el frontend no usa almacenamiento del navegador
// (tests/security/test_browser_storage.py). Sin JavaScript queda abierta y todo navega igual.
import { closeAllMenus } from "./menus.js";

const MOBILE = window.matchMedia("(max-width: 860px)");
const shell = document.querySelector("[data-shell]");
const toggle = document.querySelector("[data-sidebar-toggle]");

let open = true;

function render() {
  const expanded = MOBILE.matches ? shell.classList.contains("is-mobile-open") : open;
  shell.classList.toggle("is-collapsed", !MOBILE.matches && !open);
  toggle.setAttribute("aria-expanded", String(expanded));
  toggle.setAttribute("aria-label", expanded ? "Cerrar la barra lateral" : "Abrir la barra lateral");
}

function onToggle() {
  closeAllMenus();
  if (MOBILE.matches) {
    shell.classList.toggle("is-mobile-open");
  } else {
    open = !open;
  }
  render();
}

if (shell && toggle) {
  toggle.addEventListener("click", onToggle);
  MOBILE.addEventListener("change", () => {
    shell.classList.remove("is-mobile-open");
    render();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !shell.classList.contains("is-mobile-open")) return;
    shell.classList.remove("is-mobile-open");
    render();
    toggle.focus();
  });
  render();
}
