// Avisos del sistema: el botón de cerrar viene oculto para que, sin JavaScript, el aviso solo quede visible.
for (const button of document.querySelectorAll("[data-notice-close]")) {
  button.hidden = false;
  button.addEventListener("click", () => button.closest("[data-notice]").remove());
}
