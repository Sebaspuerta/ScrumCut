// Lo que sigue en Django a propósito (docs/decisiones/frontend-react.md): la cuenta, con sus límites de
// intentos de allauth y axes, y la descarga del Excel del tablero.
export const DJANGO_ROUTES = {
  logout: "/cuenta/logout/",
  logoutEverywhere: "/cuenta/cerrar-sesiones/",
  security: "/cuenta/2fa/",
  export: "/reportes/exportar/",
} as const;
