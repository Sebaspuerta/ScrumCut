import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/client";

/** Cambia la sede activa en el servidor; todo lo leído antes era de la sede anterior, así que se vuelve a pedir. */
export function useSwitchBranch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sede: string) => api.post("/api/v1/branch/", { sede }),
    onSuccess: () => queryClient.invalidateQueries(),
  });
}
