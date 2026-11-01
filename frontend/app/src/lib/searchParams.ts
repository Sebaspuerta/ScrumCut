// Los filtros de las listas viven en la URL (?q=, ?pagina=…) y lo abierto en el panel, en su propia clave. El
// servidor valida cada valor: uno inválido vuelve al de siempre.
export const PAGE_PARAM = "pagina";

/** Lo que se le pide a la API: los filtros de la URL que tienen valor y la página. */
export function listQuery(params: URLSearchParams, keys: readonly string[]): Record<string, string> {
  const query: Record<string, string> = {};
  for (const key of keys) {
    const value = params.get(key);
    if (value) query[key] = value;
  }
  const page = params.get(PAGE_PARAM);
  if (page) query.page = page;
  return query;
}

/** La URL con un filtro cambiado: se vuelve a la primera página y se conserva lo abierto en el panel. */
export function withFilter(params: URLSearchParams, key: string, value: string): URLSearchParams {
  const next = new URLSearchParams(params);
  if (value) next.set(key, value);
  else next.delete(key);
  next.delete(PAGE_PARAM);
  return next;
}

/** La URL con otro valor en una sola clave (lo abierto en el panel, la página o un formulario). */
export function withParam(params: URLSearchParams, key: string, value: string | null): URLSearchParams {
  const next = new URLSearchParams(params);
  if (value === null) next.delete(key);
  else next.set(key, value);
  return next;
}
