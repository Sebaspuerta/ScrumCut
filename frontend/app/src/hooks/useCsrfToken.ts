import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";

/** El token CSRF para los formularios POST a Django (cerrar sesión); vive solo en memoria. */
export function useCsrfToken(enabled = true) {
  return useQuery({ queryKey: ["csrf"], queryFn: () => api.csrfToken(), enabled });
}
