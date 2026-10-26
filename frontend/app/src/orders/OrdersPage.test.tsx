import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderApp } from "../test/renderApp";
import { ORDER_ID, ORDER_LIST, requestsTo, stubSalesApi } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const listUrls = (fetch: ReturnType<typeof stubSalesApi>) =>
  requestsTo(fetch, "/api/v1/orders/").map((request) => request.url);

describe("lista de comandas", () => {
  it("los filtros de la URL llegan a la API", async () => {
    const fetch = stubSalesApi();
    renderApp("/comandas?estado=cerradas&fecha=2026-10-20");

    await screen.findByRole("heading", { name: "Comandas" });

    await waitFor(() => {
      expect(listUrls(fetch)).toContain("/api/v1/orders/?estado=cerradas&fecha=2026-10-20");
    });
  });

  it("las pestañas son enlaces con aria-current y cambian el estado en la URL", async () => {
    const fetch = stubSalesApi();
    renderApp("/comandas");
    const tabs = await screen.findByRole("navigation", { name: "Estado de las comandas" });

    expect(
      within(tabs)
        .getByRole("link", { name: /Abiertas/ })
        .getAttribute("aria-current"),
    ).toBe("page");
    await userEvent.click(within(tabs).getByRole("link", { name: /Cerradas hoy/ }));

    await waitFor(() => {
      expect(listUrls(fetch)).toContain("/api/v1/orders/?estado=cerradas");
    });
  });

  it("la búsqueda va a la URL al enviarla y elegir una comanda abre su detalle", async () => {
    const fetch = stubSalesApi();
    renderApp("/comandas");

    await userEvent.type(await screen.findByRole("searchbox", { name: /Buscar por cliente/ }), "laura{Enter}");
    await waitFor(() => {
      expect(listUrls(fetch)).toContain("/api/v1/orders/?q=laura");
    });
    await userEvent.click(screen.getByRole("link", { name: /Laura Gómez/ }));

    expect(await screen.findByRole("heading", { name: "Laura Gómez", level: 2 })).toBeTruthy();
    expect(requestsTo(fetch, `/api/v1/orders/${ORDER_ID}/`)).toHaveLength(1);
  });

  it("sin comandas lo dice y deja crear una", async () => {
    const all = { ...ORDER_LIST, results: [], count: 0 };
    stubSalesApi({ "/api/v1/orders/": all });
    renderApp("/comandas");

    expect(await screen.findByText("No hay comandas en esta pestaña.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Nueva comanda" })).toBeTruthy();
  });

  it("las páginas se cuentan con el tamaño que da el servidor", async () => {
    stubSalesApi({ "/api/v1/orders/": { ...ORDER_LIST, count: 60, pages: 3, page_size: 25 } });
    renderApp("/comandas");

    const pages = await screen.findByRole("navigation", { name: "Páginas de comandas" });

    expect(pages.textContent).toContain("1–25 de 60");
  });

  it("si la lista falla, lo dice y deja reintentar", async () => {
    stubSalesApi({ "/api/v1/orders/": undefined });
    renderApp("/comandas");

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeTruthy();
  });
});
