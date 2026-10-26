// Respuestas de ejemplo de la API de Comandas y Caja, con la forma de los tipos generados.
import type { CashSession, CashState, Closings, Me, OrderCatalog, OrderDetail, OrderList } from "../api/types";
import { OWNER_ME, stubOwnerApi } from "./fakeApi";

export const ORDER_ID = "0b6c6c3e-1111-4c1d-9a7f-000000000001";
export const SESSION_ID = "0b6c6c3e-2222-4c1d-9a7f-000000000002";
export const CORTE_ID = "0b6c6c3e-3333-4c1d-9a7f-000000000003";
export const ANA_ID = "0b6c6c3e-4444-4c1d-9a7f-000000000004";

export const SALES_ME: Me = {
  ...OWNER_ME,
  permissions: [
    "caja.abrir",
    "caja.cerrar",
    "caja.movimiento",
    "caja.ver",
    "clientes.ver",
    "comandas.cerrar",
    "comandas.crear",
    "comandas.descontar",
    "comandas.editar",
    "comandas.ver",
  ],
};

export const ORDER: OrderDetail = {
  id: ORDER_ID,
  number: 147,
  status: "abierta",
  client_name: "Laura Gómez",
  client: { id: "c1", name: "Laura Gómez", phone: "300 *** 4567", level: "Frecuente", visits: 4 },
  barbers: "Ana",
  items: "Corte",
  payment: "Sin cobro",
  total: "25000.00",
  created_at: "2026-10-22T13:00:00Z",
  closed_at: null,
  cancel_reason: "",
  branch: "Centro",
  editable: true,
  barber: "Ana",
  lines: [
    {
      id: "l1",
      kind: "servicio",
      kind_label: "Servicio",
      name: "Corte",
      barber: "Ana",
      quantity: 1,
      unit_price: "25000.00",
      line_total: "25000.00",
    },
  ],
  subtotal: "25000.00",
  discount: "0.00",
  discount_reason: "",
  amount_paid: "0.00",
  balance: "25000.00",
  payments: [],
  credit: { debt: "0.00", available: "150000.00" },
  actions: { edit: true, discount: true, checkout: true, cancel: true },
};

export const ORDER_LIST: OrderList = {
  tab: "abiertas",
  day: "2026-10-22",
  tabs: [
    { value: "abiertas", label: "Abiertas", count: 1 },
    { value: "cerradas", label: "Cerradas hoy", count: 0 },
    { value: "anuladas", label: "Anuladas", count: 0 },
  ],
  summary: null,
  count: 1,
  page: 1,
  pages: 1,
  page_size: 50,
  results: [ORDER],
  stale_cash: false,
};

export const CATALOG: OrderCatalog = {
  needs_branch: false,
  branch: "Centro",
  barbers: [{ id: ANA_ID, name: "Ana" }],
  services: [{ id: CORTE_ID, name: "Corte", price: "25000.00" }],
  products: [{ id: "p1", name: "Cera", price: "20000.00", stock: 5 }],
  methods: [
    { value: "efectivo", label: "Efectivo" },
    { value: "nequi", label: "Nequi" },
    { value: "bre_b", label: "Bre-B" },
  ],
  max_parts: 3,
  max_quantity: 99,
};

const STRIP_ZERO = { total: "0.00", count: 0 };

export const OPEN_SESSION: CashSession = {
  id: SESSION_ID,
  opened_at: "2026-10-22T13:00:00Z",
  opened_by: "Camila Ruiz",
  stale: false,
  opening_amount: "50000.00",
  strip: { sales: STRIP_ZERO, receivable_payments: STRIP_ZERO, expenses: STRIP_ZERO, withdrawals: STRIP_ZERO },
  expected: "50000.00",
  movements: [],
  other_media: { transfers: STRIP_ZERO, credit: STRIP_ZERO },
};

export const CASH_OPEN: CashState = {
  needs_branch: false,
  branch: "Centro",
  today: "2026-10-22",
  kind: "",
  kinds: [{ value: "", label: "Todos" }],
  manual_kinds: [{ value: "gasto", label: "Gasto" }],
  denominations: [100000, 50000, 20000, 10000, 5000, 2000, 1000],
  session: OPEN_SESSION,
  actions: { open: false, movement: true, close: true },
};

export const CASH_CLOSED: CashState = {
  ...CASH_OPEN,
  session: null,
  actions: { open: true, movement: false, close: false },
};

export const NO_CLOSINGS: Closings = { count: 0, page: 1, pages: 1, page_size: 20, results: [] };

/** La API de una persona que vende y cobra en Centro, con lo que se le quiera cambiar. */
export function stubSalesApi(overrides: Record<string, unknown> = {}) {
  return stubOwnerApi({
    "/api/v1/me/": SALES_ME,
    "/api/v1/orders/": ORDER_LIST,
    [`/api/v1/orders/${ORDER_ID}/`]: ORDER,
    "/api/v1/orders/catalog/": CATALOG,
    "/api/v1/cash/": CASH_OPEN,
    "/api/v1/cash/closings/": NO_CLOSINGS,
    ...overrides,
  });
}

function urlOf(input: RequestInfo | URL): string {
  return typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
}

/** Las peticiones que hizo la app a una ruta de la API con un método, con su URL y su cuerpo. */
export function requestsTo(fetch: ReturnType<typeof stubOwnerApi>, path: string, method = "GET") {
  return fetch.mock.calls
    .filter(([input, init]) => urlOf(input).split("?")[0] === path && (init?.method ?? "GET") === method)
    .map(([input, init]) => ({
      url: urlOf(input),
      body: typeof init?.body === "string" ? (JSON.parse(init.body) as unknown) : null,
    }));
}

/** Cambia la respuesta de una sola ruta (un error, o una que tarda) y deja las demás como estaban. */
export function respondAt(fetch: ReturnType<typeof stubOwnerApi>, path: string, respond: () => Promise<Response>) {
  const fallback = fetch.getMockImplementation();
  fetch.mockImplementation((input, init) =>
    urlOf(input) === path ? respond() : (fallback?.(input, init) ?? Promise.resolve(new Response("{}"))),
  );
}
