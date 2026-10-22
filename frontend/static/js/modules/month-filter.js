// Selector de mes del tablero: con JavaScript se aplica al elegir; sin él, con el botón "Ver".
const form = document.querySelector("[data-month-filter]");

if (form) {
  form.querySelector("[data-month-submit]").hidden = true;
  form.querySelector("select").addEventListener("change", () => form.requestSubmit());
}
