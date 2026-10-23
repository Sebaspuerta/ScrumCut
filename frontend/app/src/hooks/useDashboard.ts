import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "../api/client";

export const DASHBOARD_KEY = ["dashboard"] as const;

/** El tablero del mes (AAAA-MM; sin mes, el actual). El servidor valida el mes, el permiso y el alcance de sede. */
export function useDashboard(month: string | null, enabled: boolean) {
  return useQuery({
    queryKey: [...DASHBOARD_KEY, month ?? "actual"],
    queryFn: () => api.get("/api/v1/dashboard/", month ? { mes: month } : undefined),
    placeholderData: keepPreviousData,
    enabled,
  });
}
