import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";

/** Las alertas del panel de la campana; se piden al abrirlo. */
export function useNotifications(enabled: boolean) {
  return useQuery({ queryKey: ["notifications"], queryFn: () => api.get("/api/v1/notifications/"), enabled });
}
