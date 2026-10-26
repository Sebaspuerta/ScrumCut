import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";

export const ME_KEY = ["me"] as const;
// La zona por defecto de toda barbería nueva (tenancy.Barbershop.timezone); el marco ya la trae cargada.
const DEFAULT_TIME_ZONE = "America/Bogota";

/** La persona, su barbería activa, su rol, sus permisos y su sede, tal como los decide el servidor. */
export function useMe() {
  return useQuery({ queryKey: ME_KEY, queryFn: () => api.get("/api/v1/me/") });
}

/** La zona horaria de la barbería activa: «hoy» y las horas se leen en ella. */
export function useTimeZone(): string {
  return useMe().data?.barbershop?.timezone ?? DEFAULT_TIME_ZONE;
}
