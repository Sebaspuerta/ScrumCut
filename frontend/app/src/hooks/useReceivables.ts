import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { RECEIVABLES_KEY } from "./useWriteMutation";

/** La cartera de la sede, la antigüedad y una página de la pestaña elegida (filtros de la URL). */
export function useReceivables(query: Record<string, string>, enabled: boolean) {
  return useQuery({
    queryKey: [...RECEIVABLES_KEY, "list", query],
    queryFn: () => api.get("/api/v1/receivables/", query),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** El fiado con su comanda, sus abonos, las formas de pago y si el rol puede abonar aquí. */
export function useReceivable(id: string | null) {
  return useQuery({
    queryKey: [...RECEIVABLES_KEY, "detail", id],
    queryFn: () => api.get("/api/v1/receivables/{public_id}/", undefined, { public_id: id ?? "" }),
    enabled: id !== null,
  });
}
