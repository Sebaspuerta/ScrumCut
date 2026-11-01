import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback, useRef } from "react";

import { DASHBOARD_KEY } from "./useDashboard";

export const ORDERS_KEY = ["orders"] as const;
export const CASH_KEY = ["cash"] as const;
export const CLIENTS_KEY = ["clients"] as const;
export const RECEIVABLES_KEY = ["receivables"] as const;

/** Después de escribir se vuelven a pedir comandas, caja, clientes, fiados y tablero: un cobro cambia la deuda y el
 * nivel del cliente, un abono la caja, y un cliente editado sale en comandas y fiados. Nada se actualiza a mano. */
function refreshAll(queryClient: QueryClient): Promise<unknown> {
  return Promise.all(
    [ORDERS_KEY, CASH_KEY, CLIENTS_KEY, RECEIVABLES_KEY, DASHBOARD_KEY].map((queryKey) =>
      queryClient.invalidateQueries({ queryKey }),
    ),
  );
}

/**
 * Una escritura de comandas, caja, fiados o clientes. `submit` ignora un segundo envío mientras el primero sigue en curso
 * (doble clic) y la mutación sigue pendiente hasta que llegan los datos nuevos, así que el botón queda
 * deshabilitado hasta entonces. El servidor igual bloquea la fila: dos pestañas no cobran dos veces.
 */
export function useWriteMutation<TVariables, TData>(mutationFn: (variables: TVariables) => Promise<TData>) {
  const queryClient = useQueryClient();
  const inFlight = useRef(false);
  // El aviso de éxito va antes de volver a pedir los datos: si los datos nuevos desmontan el formulario
  // (la caja cerrada ya no muestra el arqueo), el aviso igual llega.
  const succeeded = useRef<((data: TData) => void) | null>(null);
  const mutation = useMutation<TData, Error, TVariables>({
    mutationFn,
    onSuccess: (data) => {
      succeeded.current?.(data);
    },
    onSettled: () => {
      inFlight.current = false;
      return refreshAll(queryClient);
    },
  });
  const { mutate } = mutation;
  const submit = useCallback(
    (variables: TVariables, onSuccess?: (data: TData) => void) => {
      if (inFlight.current) return;
      inFlight.current = true;
      succeeded.current = onSuccess ?? null;
      mutate(variables);
    },
    [mutate],
  );
  return { ...mutation, submit };
}
