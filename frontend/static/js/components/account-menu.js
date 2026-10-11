// Mejora del menú de la cuenta: el <details> nativo ya abre y cierra sin JavaScript;
// aquí solo se agrega cerrar con Escape (devolviendo el foco al summary) y con clic fuera.
export default () => ({
  close() {
    this.$root.open = false;
  },

  closeAndFocus() {
    if (!this.$root.open) return;
    this.$root.open = false;
    this.$refs.summary.focus();
  },
});
