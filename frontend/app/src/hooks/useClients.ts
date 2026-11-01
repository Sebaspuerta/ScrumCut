import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { CLIENTS_KEY } from "./useWriteMutation";

/** La lista de la sede con sus filtros (los de la URL), sus cuatro cifras y la política de datos vigente. */
export function useClients(query: Record<string, string>, enabled: boolean) {
  return useQuery({
    queryKey: [...CLIENTS_KEY, "list", query],
    queryFn: () => api.get("/api/v1/clients/", query),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** La ficha: su identidad, y su nivel, historial y fiados en la sede (sin nada de otra sede). */
export function useClient(id: string | null) {
  return useQuery({
    queryKey: [...CLIENTS_KEY, "detail", id],
    queryFn: () => api.get("/api/v1/clients/{public_id}/", undefined, { public_id: id ?? "" }),
    enabled: id !== null,
  });
}
