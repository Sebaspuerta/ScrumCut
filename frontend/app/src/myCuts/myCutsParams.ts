// El día de la lista de «Mis cortes» (?fecha=) y su página (?pagina=, en lib/searchParams.ts). El barbero no va en
// la URL: el servidor lo toma de la sesión.
import { listQuery } from "../lib/searchParams";

export const DAY_PARAM = "fecha";

export function myCutsQuery(params: URLSearchParams): Record<string, string> {
  return listQuery(params, [DAY_PARAM]);
}
