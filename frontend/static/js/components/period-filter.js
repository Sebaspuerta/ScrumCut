// Filtro de período del tablero: aplica al cambiar, salvo el rango, que espera las dos fechas.
export default () => ({
  custom: false,

  init() {
    this.custom = this.$root.dataset.custom === "true";
  },

  apply() {
    this.$root.requestSubmit();
  },

  periodChanged(event) {
    this.custom = event.target.value === "rango";
    if (!this.custom) this.apply();
  },
});
