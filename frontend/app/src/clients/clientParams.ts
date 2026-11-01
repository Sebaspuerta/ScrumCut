// Los filtros de la lista de clientes (?q=, ?nivel=, ?orden=, ?pagina=), el cliente abierto en la ficha
// (?cliente=, en lib/appRoutes.ts) y los formularios (?nuevo=1, ?editar=1).
export const FILTER_KEYS = ["q", "nivel", "orden"] as const;
export const NEW_PARAM = "nuevo";
export const EDIT_PARAM = "editar";
