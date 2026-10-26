// Los filtros de la lista de comandas viven en la URL (?estado=, ?fecha=, ?q=, ?barbero=, ?pagina=) y la
// comanda abierta en el panel, en ?comanda=. El servidor valida cada valor: uno inválido vuelve al de siempre.
export const FILTER_KEYS = ["estado", "fecha", "q", "barbero"] as const;
export const ORDER_PARAM = "comanda";
export const NEW_PARAM = "nueva";
export const PAGE_PARAM = "pagina";

/** Lo que se le pide a la API: los filtros de la URL que tienen valor y la página. */
export function listQuery(params: URLSearchParams): Record<string, string> {
  const query: Record<string, string> = {};
  for (const key of FILTER_KEYS) {
    const value = params.get(key);
    if (value) query[key] = value;
  }
  const page = params.get(PAGE_PARAM);
  if (page) query.page = page;
  return query;
}

/** La URL con un filtro cambiado: se vuelve a la primera página y se conserva la comanda abierta. */
export function withFilter(params: URLSearchParams, key: string, value: string): URLSearchParams {
  const next = new URLSearchParams(params);
  if (value) next.set(key, value);
  else next.delete(key);
  next.delete(PAGE_PARAM);
  return next;
}

/** La URL con otro valor en una sola clave (la comanda, la página o el formulario nuevo). */
export function withParam(params: URLSearchParams, key: string, value: string | null): URLSearchParams {
  const next = new URLSearchParams(params);
  if (value === null) next.delete(key);
  else next.set(key, value);
  return next;
}
