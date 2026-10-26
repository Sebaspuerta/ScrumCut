import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { CASH_KEY } from "./useMoneyMutation";

/** La caja de la sede: su sesión, la franja, los movimientos (filtrados por ?tipo=) y lo que el rol puede hacer. */
export function useCash(kind: string, enabled = true) {
  return useQuery({
    queryKey: [...CASH_KEY, "state", kind],
    queryFn: () => api.get("/api/v1/cash/", kind ? { tipo: kind } : undefined),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** El historial de cierres de la sede, por páginas. */
export function useClosings(page: string) {
  return useQuery({
    queryKey: [...CASH_KEY, "closings", page],
    queryFn: () => api.get("/api/v1/cash/closings/", { page }),
    placeholderData: keepPreviousData,
  });
}
