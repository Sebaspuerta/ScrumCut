import { vi } from "vitest";

import type { CalendarDay, Dashboard, Me, Navigation } from "../api/types";

export const OWNER_ME: Me = {
  user: { email: "dueno@example.com", name: "Laura Peña", initials: "LP", theme: "system" },
  barbershop: { name: "Barbería Demo", initials: "BD", timezone: "America/Bogota" },
  role: { code: "owner", label: "Dueño" },
  permissions: ["alertas.ver", "caja.ver", "reportes.exportar", "reportes.ver", "sedes.ver"],
  branch: {
    mode: "una",
    current_label: "Centro",
    options: [
      { token: "centro", label: "Centro", current: true },
      { token: "norte", label: "Norte", current: false },
    ],
    can_view_all: true,
    can_manage: true,
  },
};

export const CASHIER_ME: Me = {
  ...OWNER_ME,
  role: { code: "cashier", label: "Cajero" },
  permissions: ["alertas.ver", "caja.ver", "reportes.ver"],
  branch: {
    mode: "una",
    current_label: "Centro",
    options: [{ token: "centro", label: "Centro", current: true }],
    can_view_all: false,
    can_manage: false,
  },
};

export const NAVIGATION: Navigation = {
  sidebar: [
    {
      title: "Operación",
      items: [
        { label: "Tablero", icon: "layout-dashboard", url: "/", app_path: "/", status: "enlace" },
        { label: "Agenda", icon: "calendar", url: null, app_path: null, status: "pronto" },
        { label: "Comandas", icon: "receipt", url: "/comandas/", app_path: null, status: "enlace" },
      ],
    },
  ],
  administration: [],
  administration_summary: null,
  new_actions: [{ label: "Nueva comanda", icon: "receipt", url: "/comandas/nueva/", app_path: null, status: "enlace" }],
  unread_alerts: 3,
};

function day(date: string, overrides: Partial<CalendarDay> = {}): CalendarDay {
  const number = Number(date.slice(-2));
  return {
    date,
    day: number,
    total: "0.00",
    level: 0,
    ratio: 0,
    today: false,
    future: false,
    has_sales: false,
    orders: 0,
    ticket: null,
    ...overrides,
  };
}

/** Octubre de 2026 empieza en jueves: tres casillas vacías antes del día 1. */
const FIRST_WEEK: Dashboard["calendar"]["weeks"][number] = {
  days: [
    day("2026-10-01", { total: "125000.00", level: 4, ratio: 1, has_sales: true, orders: 5, ticket: "25000.00" }),
    day("2026-10-02"),
    day("2026-10-03", {
      today: true,
      total: "40000.00",
      level: 1,
      ratio: 0.32,
      has_sales: true,
      orders: 2,
      ticket: "20000.00",
    }),
    day("2026-10-04", { future: true }),
  ],
  total: "165000.00",
};

export const DASHBOARD: Dashboard = {
  month: "2026-10",
  month_label: "Octubre 2026",
  previous_month: "2026-09",
  next_month: null,
  today: "2026-10-03",
  timezone: "America/Bogota",
  scope_label: "Centro",
  stale_cash: false,
  kpis: {
    comparison: "vs. sábado anterior a esta hora",
    income: { value: "3440000.00", variation: { percent: "12.4", direction: "up" } },
    orders: { value: 47, open: 8, variation: null },
    ticket: { value: "73191.00", variation: { percent: "-3.1", direction: "down" } },
    cash: { expected: "1284000.00", opened_at: "2026-10-03T13:02:00Z" },
    receivables: {
      pending_count: 6,
      pending_balance: "682000.00",
      overdue_count: 4,
      overdue_balance: "80000.00",
      clients: 5,
    },
  },
  trend: { income: ["10.00", "20.00", "15.00"], orders: [1, 3, 2], ticket: ["10.00", "12.00", "9.00"] },
  calendar: {
    weeks: [FIRST_WEEK],
    total: "165000.00",
    selling_days: 2,
    daily_average: "82500.00",
    best: null,
    last_sale: null,
  },
  cash: { needs_branch: false, flow: null },
  unread_alerts: 0,
  barbers: [],
  products: [],
  closings: [],
  alerts: [],
};

function pathOf(input: RequestInfo | URL): string {
  const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  return raw.split("?")[0] ?? raw;
}

/** fetch falso: cada ruta de la API responde con su cuerpo; una ruta sin cuerpo, 404 (sin reintentos). */
export function stubApi(bodies: Record<string, unknown>) {
  const fetch = vi.fn<typeof globalThis.fetch>((input) => {
    const body = bodies[pathOf(input)];
    const status = body === undefined ? 404 : 200;
    return Promise.resolve(new Response(JSON.stringify(body ?? {}), { status }));
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

/** La API completa de un dueño, con lo que se le quiera cambiar. */
export function stubOwnerApi(overrides: Record<string, unknown> = {}) {
  return stubApi({
    "/api/v1/me/": OWNER_ME,
    "/api/v1/navigation/": NAVIGATION,
    "/api/v1/dashboard/": DASHBOARD,
    "/api/v1/csrf/": { csrf_token: "token-de-prueba" },
    "/api/v1/me/preferences/": { theme: "dark" },
    ...overrides,
  });
}
