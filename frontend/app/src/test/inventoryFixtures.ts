// Respuestas de ejemplo de la API de Inventario, con la forma de los tipos generados.
import type { InventoryProduct, Me, ProductDetail, ProductList, StockAlerts } from "../api/types";
import { OWNER_ME, stubOwnerApi } from "./fakeApi";

export const CERA_ID = "0b6c6c3e-7777-4c1d-9a7f-000000000007";
export const NORTE_ID = "0b6c6c3e-8888-4c1d-9a7f-000000000008";
export const CUIDADO_ID = "0b6c6c3e-9999-4c1d-9a7f-000000000009";

export const INVENTORY_ME: Me = {
  ...OWNER_ME,
  permissions: [
    "inventario.ajustar",
    "inventario.crear",
    "inventario.editar",
    "inventario.eliminar",
    "inventario.ver",
    "sedes.ver",
  ],
};

export const CERA_ROW: InventoryProduct = {
  id: CERA_ID,
  name: "Cera mate",
  category: "Cuidado",
  product_type: "venta",
  type_label: "Venta",
  photo: null,
  stock: 5,
  price: "22000.00",
  minimum_stock: 6,
  low_stock: true,
  is_active: true,
  levels: [{ branch: "Centro", quantity: 5, low: true }],
};

export const PRODUCT_LIST: ProductList = {
  search: "",
  category: "",
  product_type: "",
  status: "activos",
  categories: [{ value: CUIDADO_ID, label: "Cuidado" }],
  types: [
    { value: "venta", label: "Venta" },
    { value: "consumible", label: "Consumible interno" },
    { value: "perecedero", label: "Perecedero" },
  ],
  statuses: [
    { value: "activos", label: "Activos" },
    { value: "inactivos", label: "Inactivos" },
    { value: "todos", label: "Todos" },
  ],
  count: 1,
  page: 1,
  pages: 1,
  page_size: 50,
  results: [CERA_ROW],
};

export const CERA: ProductDetail = {
  ...CERA_ROW,
  category: { id: CUIDADO_ID, name: "Cuidado" },
  purchase_cost: "8000.00",
  sale_price: "20000.00",
  branch_price: "22000.00",
  expiration_date: null,
  supplier: "Proveedor Sur",
  branch: "Centro",
  movements: {
    count: 1,
    page: 1,
    pages: 1,
    page_size: 20,
    results: [
      {
        id: "m1",
        at: "2026-10-20T15:00:00Z",
        kind: "entrada",
        kind_label: "Entrada",
        branch: "Centro",
        quantity: 5,
        stock_before: 0,
        stock_after: 5,
        unit_cost: "8000.00",
        reason: "Inventario inicial",
        by: "Laura Peña",
      },
    ],
  },
  destinations: [{ id: NORTE_ID, name: "Norte", stock: 3 }],
  actions: { edit: true, delete: true, adjust: true, branch_price: true },
  needs_branch: false,
};

export const STOCK_ALERTS: StockAlerts = {
  low_stock: [
    {
      product: CERA_ID,
      name: "Cera mate",
      branch: "Centro",
      quantity: 5,
      minimum_stock: 6,
      expiration_date: null,
      expired: false,
    },
  ],
  low_stock_count: 1,
  expiring: [],
  expiring_count: 0,
};

export const CERA_PATH = `/api/v1/inventory/products/${CERA_ID}/`;

/** La API de un dueño con el inventario de Centro: la Cera mate con stock bajo y su detalle. */
export function stubInventoryApi(overrides: Record<string, unknown> = {}) {
  return stubOwnerApi({
    "/api/v1/me/": INVENTORY_ME,
    "/api/v1/inventory/products/": PRODUCT_LIST,
    "/api/v1/inventory/alerts/": STOCK_ALERTS,
    "/api/v1/inventory/categories/": { results: [{ id: CUIDADO_ID, name: "Cuidado" }] },
    [CERA_PATH]: CERA,
    ...overrides,
  });
}
