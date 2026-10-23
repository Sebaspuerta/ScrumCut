import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";

export const ME_KEY = ["me"] as const;

/** La persona, su barbería activa, su rol, sus permisos y su sede, tal como los decide el servidor. */
export function useMe() {
  return useQuery({ queryKey: ME_KEY, queryFn: () => api.get("/api/v1/me/") });
}
