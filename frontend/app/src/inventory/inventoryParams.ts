// Los filtros de la lista de productos (?q=, ?categoria=, ?tipo=, ?estado=, ?pagina=), el producto abierto
// (?producto=, en lib/appRoutes.ts), la página de su historial (?movimientos=) y los diálogos: nuevo, editar,
// categorías y mover stock (?mover=entrada|ajuste|traslado).
export const FILTER_KEYS = ["q", "categoria", "tipo", "estado"] as const;
export const NEW_PARAM = "nuevo";
export const EDIT_PARAM = "editar";
export const CATEGORIES_PARAM = "categorias";
export const MOVE_PARAM = "mover";
export const HISTORY_PARAM = "movimientos";

export const MOVES = ["entrada", "ajuste", "traslado"] as const;
export type Move = (typeof MOVES)[number];

export function moveOf(params: URLSearchParams): Move | null {
  const value = params.get(MOVE_PARAM);
  return MOVES.find((move) => move === value) ?? null;
}
