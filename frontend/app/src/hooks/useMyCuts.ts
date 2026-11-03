import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { MY_CUTS_KEY } from "./useWriteMutation";

/** «Mis cortes» del barbero de la sesión: el servidor lo toma de la sesión y aplica la sede; aquí solo el día y la
 * página de la URL. */
export function useMyCuts(query: Record<string, string>) {
  return useQuery({
    queryKey: [...MY_CUTS_KEY, query],
    queryFn: () => api.get("/api/v1/my-cuts/", query),
    placeholderData: keepPreviousData,
  });
}
