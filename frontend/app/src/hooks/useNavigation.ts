import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";

export const NAVIGATION_KEY = ["navigation"] as const;

/** Los grupos e ítems que el rol puede ver y el contador de alertas de la sede activa. */
export function useNavigation(enabled: boolean) {
  return useQuery({ queryKey: NAVIGATION_KEY, queryFn: () => api.get("/api/v1/navigation/"), enabled });
}
