import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Me, MyCuts } from "../api/types";
import { OWNER_ME, stubOwnerApi } from "../test/fakeApi";
import { renderApp } from "../test/renderApp";
import { requestsTo } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const MY_CUTS_PATH = "/api/v1/my-cuts/";

const BARBER_ME: Me = {
  ...OWNER_ME,
  role: { code: "barber", label: "Barbero" },
  permissions: ["clientes.ver", "comandas.cerrar", "comandas.crear", "comandas.editar", "comandas.ver"],
};

const MY_CUTS: MyCuts = {
  barber: "Ana",
  day: "2026-10-22",
  today: { orders: 2, cuts: 2, production: "50000.00", commission: "20000.00" },
  month: { orders: 31, cuts: 34, production: "870000.00", commission: "348000.00" },
  count: 2,
  page: 1,
  pages: 1,
  page_size: 20,
  results: [
    {
      id: "o2",
      number: 149,
      closed_at: "2026-10-22T16:30:00Z",
      items: "Corte, Barba",
      cuts: 2,
      production: "40000.00",
      commission: "16000.00",
    },
    {
      id: "o1",
      number: 147,
      closed_at: "2026-10-22T14:05:00Z",
      items: "Corte",
      cuts: 1,
      production: "10000.00",
      commission: "4000.00",
    },
  ],
};

function stubBarberApi(myCuts: MyCuts = MY_CUTS) {
  return stubOwnerApi({ "/api/v1/me/": BARBER_ME, [MY_CUTS_PATH]: myCuts });
}

describe("Mis cortes", () => {
  it("el barbero ve hoy, el mes y sus comandas del día en vez del tablero ejecutivo", async () => {
    const fetch = stubBarberApi();
    renderApp("/");

    expect(await screen.findByRole("heading", { name: "Mis cortes" })).toBeTruthy();
    const today = screen.getByRole("list", { name: "Hoy" });
    expect(within(today).getByText("$20.000")).toBeTruthy();
    expect(within(screen.getByRole("list", { name: "Este mes" })).getByText("$348.000")).toBeTruthy();
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      "#149 · 11:30 a. m.Corte, Barba$40.000$16.000",
      "#147 · 9:05 a. m.Corte$10.000$4.000",
    ]);
    expect(requestsTo(fetch, "/api/v1/dashboard/")).toEqual([]);
  });

  it("el día va en la URL y cambiarlo pide ese día, sin enviar nunca un barbero", async () => {
    const fetch = stubBarberApi();
    renderApp("/?fecha=2026-10-20");
    const day = await screen.findByLabelText("Día");

    fireEvent.change(day, { target: { value: "2026-10-21" } });

    await waitFor(() => {
      expect(requestsTo(fetch, MY_CUTS_PATH).map((request) => request.url)).toEqual([
        `${MY_CUTS_PATH}?fecha=2026-10-20`,
        `${MY_CUTS_PATH}?fecha=2026-10-21`,
      ]);
    });
  });

  it("sin comandas cerradas ese día lo dice", async () => {
    stubBarberApi({ ...MY_CUTS, count: 0, results: [] });
    renderApp("/");

    expect(await screen.findByText("No tienes cortes registrados este día.")).toBeTruthy();
  });

  it("sin un barbero vinculado lo explica", async () => {
    stubBarberApi({ ...MY_CUTS, barber: null, results: [] });
    renderApp("/");

    expect(await screen.findByText(/no está vinculado a un barbero/)).toBeTruthy();
  });

  it("si falla muestra el error con la opción de reintentar", async () => {
    stubOwnerApi({ "/api/v1/me/": BARBER_ME }); // sin respuesta para «Mis cortes»: 404, sin reintentos
    renderApp("/");

    expect((await screen.findByRole("alert")).textContent).toContain("No pudimos cargar tus cortes.");
  });
});
