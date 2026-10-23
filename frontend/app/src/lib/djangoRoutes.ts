// Pantallas y acciones que siguen en Django mientras no existan en la app de React. Las rutas que
// dependen de permisos o de datos llegan por la API (navigation); estas son fijas de la cuenta y del tablero.
export const DJANGO_ROUTES = {
  logout: "/cuenta/logout/",
  logoutEverywhere: "/cuenta/cerrar-sesiones/",
  security: "/cuenta/2fa/",
  cash: "/caja/",
  export: "/reportes/exportar/",
} as const;
