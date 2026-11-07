import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { INVENTORY_KEY } from "./useWriteMutation";

/** El catálogo con sus filtros (los de la URL), con la existencia y el precio de la sede. */
export function useProducts(query: Record<string, string>, enabled: boolean) {
  return useQuery({
    queryKey: [...INVENTORY_KEY, "list", query],
    queryFn: () => api.get("/api/v1/inventory/products/", query),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** El producto con sus existencias por sede y una página de su historial. */
export function useProduct(id: string | null, page = "1") {
  return useQuery({
    queryKey: [...INVENTORY_KEY, "detail", id, page],
    queryFn: () => api.get("/api/v1/inventory/products/{public_id}/", { page }, { public_id: id ?? "" }),
    placeholderData: keepPreviousData,
    enabled: id !== null,
  });
}

/** Stock bajo y perecederos por vencer de la sede. */
export function useStockAlerts(enabled: boolean) {
  return useQuery({
    queryKey: [...INVENTORY_KEY, "alerts"],
    queryFn: () => api.get("/api/v1/inventory/alerts/"),
    enabled,
  });
}

export function useCategories(enabled: boolean) {
  return useQuery({
    queryKey: [...INVENTORY_KEY, "categories"],
    queryFn: () => api.get("/api/v1/inventory/categories/"),
    enabled,
  });
}
