// Menús de la barra superior. Son <details>: abren y cierran sin JavaScript. Aquí se agrega
// que haya uno solo abierto, que se cierren con Esc o con un clic fuera, aria-expanded al día
// y el foco de vuelta al botón al cerrar con el teclado.
const menus = [...document.querySelectorAll("[data-menu]")];

const summaryOf = (menu) => menu.querySelector(":scope > summary");

function close(menu, { focus = false } = {}) {
  if (!menu.open) return;
  menu.open = false;
  if (focus) summaryOf(menu).focus();
}

function syncExpanded(menu) {
  summaryOf(menu).setAttribute("aria-expanded", String(menu.open));
  if (!menu.open) return;
  for (const other of menus) if (other !== menu) close(other);
}

export function closeAllMenus() {
  for (const menu of menus) close(menu);
}

for (const menu of menus) {
  menu.addEventListener("toggle", () => syncExpanded(menu));
}

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  const open = menus.find((menu) => menu.open);
  if (open) close(open, { focus: true });
});

document.addEventListener("click", (event) => {
  for (const menu of menus) if (!menu.contains(event.target)) close(menu);
});
