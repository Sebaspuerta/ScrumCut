import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { ORDERS_KEY } from "./useMoneyMutation";

/** La lista de una pestaña con sus filtros (los de la URL); el servidor aplica el alcance de sede y del rol. */
export function useOrders(query: Record<string, string>, enabled: boolean) {
  return useQuery({
    queryKey: [...ORDERS_KEY, "list", query],
    queryFn: () => api.get("/api/v1/orders/", query),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** Una comanda con sus líneas, su cliente, su fiado posible y lo que el rol puede hacer con ella. */
export function useOrder(id: string | null) {
  return useQuery({
    queryKey: [...ORDERS_KEY, "detail", id],
    queryFn: () => api.get("/api/v1/orders/{public_id}/", undefined, { public_id: id ?? "" }),
    enabled: id !== null,
  });
}

/** Barberos, servicios y productos con el precio y el stock de la sede, y las formas de pago habilitadas. */
export function useOrderCatalog(enabled = true) {
  return useQuery({ queryKey: [...ORDERS_KEY, "catalog"], queryFn: () => api.get("/api/v1/orders/catalog/"), enabled });
}

/** Clientes de la barbería por nombre, celular o documento; solo nombre y celular enmascarado. */
export function useClientSearch(term: string) {
  const wanted = term.trim();
  return useQuery({
    queryKey: ["clients", "search", wanted],
    queryFn: () => api.get("/api/v1/clients/search/", { q: wanted }),
    enabled: wanted.length > 0,
  });
}
