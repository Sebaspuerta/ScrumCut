// Menú lateral y panel del asistente. El estado no se guarda: sin almacenamiento en el navegador.
export default () => ({
  sideOpen: true,
  chatOpen: false,

  toggleSide() {
    this.sideOpen = !this.sideOpen;
  },

  toggleChat() {
    this.chatOpen = !this.chatOpen;
  },

  get shellClass() {
    return { "is-collapsed": !this.sideOpen };
  },

  get sideExpanded() {
    return String(this.sideOpen);
  },

  get sideLabel() {
    return this.sideOpen ? "Ocultar menú de módulos" : "Mostrar menú de módulos";
  },

  get chatExpanded() {
    return String(this.chatOpen);
  },

  get chatLabel() {
    return this.chatOpen ? "Ocultar asistente" : "Abrir asistente";
  },

  get chatButtonClass() {
    return { "is-active": this.chatOpen };
  },
});
