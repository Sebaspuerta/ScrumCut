// Los filtros de la lista de comandas (?estado=, ?fecha=, ?q=, ?barbero=, ?pagina=) y la comanda abierta en el
// panel (?comanda=, en lib/appRoutes.ts); los ayudantes de la URL están en lib/searchParams.ts.
import { listQuery } from "../lib/searchParams";

export const FILTER_KEYS = ["estado", "fecha", "q", "barbero"] as const;
export const NEW_PARAM = "nueva";

export function orderListQuery(params: URLSearchParams): Record<string, string> {
  return listQuery(params, FILTER_KEYS);
}
