// Respuestas de ejemplo de la API de Clientes y Fiados, con la forma de los tipos generados.
import type { ClientDetail, ClientList, ClientRow, Me, ReceivableDetail, ReceivableList } from "../api/types";
import { OWNER_ME, stubOwnerApi } from "./fakeApi";

export const LAURA_ID = "0b6c6c3e-5555-4c1d-9a7f-000000000005";
export const DEBT_ID = "0b6c6c3e-6666-4c1d-9a7f-000000000006";

export const CLIENTS_ME: Me = {
  ...OWNER_ME,
  permissions: ["clientes.crear", "clientes.editar", "clientes.ver", "comandas.crear", "fiados.abonar", "fiados.ver"],
};

export const LAURA_ROW: ClientRow = {
  id: LAURA_ID,
  name: "Laura Gómez",
  phone: "300 *** 4567",
  has_activity: true,
  level: "debtor",
  level_label: "Deudor",
  visits: 4,
  last_visit: "2026-10-20T15:00:00Z",
  spent_recent: "100000.00",
  debt: "25000.00",
};

export const CLIENT_LIST: ClientList = {
  search: "",
  level: "",
  order: "ultima",
  levels: [
    { value: "", label: "Todos", count: 1 },
    { value: "debtor", label: "Deudor", count: 1 },
    { value: "vip", label: "VIP", count: 0 },
  ],
  orderings: [
    { value: "ultima", label: "Última visita" },
    { value: "deuda", label: "Mayor deuda" },
  ],
  stats: {
    active: 1,
    with_visits: 1,
    new_this_month: 1,
    new_last_month: 0,
    return_rate: null,
    debtors: 1,
    debt_total: "25000.00",
  },
  count: 1,
  page: 1,
  pages: 1,
  page_size: 50,
  results: [LAURA_ROW],
  data_policy: { version: "2026-10", url: "/legal/tratamiento-de-datos/" },
};

export const LAURA: ClientDetail = {
  id: LAURA_ID,
  name: "Laura Gómez",
  initials: "LG",
  phone: "300 *** 4567",
  email: "laura@correo.test",
  notes: "Degradado bajo",
  since: "2025-03-10T15:00:00Z",
  activity: {
    level: "debtor",
    level_label: "Deudor",
    progress: { next: "Frecuente", missing: 1, percent: 75 },
    visits: 4,
    spent: "100000.00",
    ticket: "25000.00",
    barber: { name: "Ana", visits: 3 },
    favorite: "Corte",
    balance: "25000.00",
    open_debt: DEBT_ID,
    last_visits: [],
  },
  receivables: [],
  actions: { edit: true, new_order: true },
};

export const DEBT: ReceivableDetail = {
  id: DEBT_ID,
  client: { id: LAURA_ID, name: "Laura Gómez" },
  order: null,
  branch: "Centro",
  created_at: "2026-10-01T15:00:00Z",
  due_date: null,
  total: "25000.00",
  paid: "0.00",
  balance: "25000.00",
  status: "pendiente",
  due_text: "Al día",
  due_tone: "ok",
  notes: "",
  payments: [],
  methods: [
    { value: "efectivo", label: "Efectivo" },
    { value: "nequi", label: "Nequi" },
  ],
  actions: { pay: true },
  needs_branch: false,
};

export const RECEIVABLE_LIST: ReceivableList = {
  today: "2026-10-22",
  tab: "pendientes",
  tabs: [
    { value: "pendientes", label: "Pendientes", count: 1 },
    { value: "vencidos", label: "Vencidos", count: 0 },
    { value: "pagados", label: "Pagados en el mes", count: 0 },
  ],
  portfolio: {
    pending: { total: "25000.00", count: 1, clients: 1 },
    overdue: { total: "0.00", clients: 0, share: 0 },
    due_soon: { total: "0.00", clients: 0 },
    collected: { total: "0.00", count: 0 },
  },
  aging: [
    { key: "current", label: "Al día", amount: "25000.00", percent: 100 },
    { key: "d1_15", label: "Vencido 1 a 15 días", amount: "0.00", percent: 0 },
  ],
  count: 1,
  page: 1,
  pages: 1,
  page_size: 50,
  results: [DEBT],
};

/** La API de una persona que atiende clientes y fiados en Centro, con lo que se le quiera cambiar. */
export function stubClientsApi(overrides: Record<string, unknown> = {}) {
  return stubOwnerApi({
    "/api/v1/me/": CLIENTS_ME,
    "/api/v1/clients/": CLIENT_LIST,
    [`/api/v1/clients/${LAURA_ID}/`]: LAURA,
    "/api/v1/receivables/": RECEIVABLE_LIST,
    [`/api/v1/receivables/${DEBT_ID}/`]: DEBT,
    ...overrides,
  });
}
