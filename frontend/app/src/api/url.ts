// Las rutas de la API con sus parámetros y su consulta, cada valor codificado para la URL.

/** /api/v1/orders/{public_id}/ con sus parámetros, cada uno codificado para la URL. */
export function fill(path: string, params: Record<string, string> = {}): string {
  return path.replace(/\{(\w+)\}/g, (_, name: string) => encodeURIComponent(params[name] ?? ""));
}

export function withQuery(path: string, query?: Record<string, string>): string {
  return query ? `${path}?${new URLSearchParams(query).toString()}` : path;
}
