import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderApp } from "../test/renderApp";
import {
  CASH_CLOSED,
  CASH_OPEN,
  OPEN_SESSION,
  requestsTo,
  respondAt,
  SESSION_ID,
  stubSalesApi,
} from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const OPEN = "/api/v1/cash/open/";
const CLOSE = `/api/v1/cash/${SESSION_ID}/close/`;
const CLOSING = {
  id: "x",
  branch: "Centro",
  closed_at: "2026-10-22T23:00:00Z",
  closed_by: "Camila Ruiz",
  expected: "50000.00",
  counted: "40000.00",
  difference: "-10000.00",
  notes: "Vueltas",
};

describe("caja", () => {
  it("se abre con la base escrita, sin decimales ni puntos", async () => {
    const fetch = stubSalesApi({ "/api/v1/cash/": CASH_CLOSED, [OPEN]: CASH_OPEN });
    renderApp("/caja");

    await userEvent.type(await screen.findByLabelText("Base de apertura"), "50.000");
    await userEvent.click(screen.getByRole("button", { name: "Abrir caja" }));

    await waitFor(() => {
      expect(requestsTo(fetch, OPEN, "POST")[0]?.body).toEqual({ opening_amount: "50000" });
    });
  });

  it("el arqueo muestra el contado y la diferencia con flecha, y con diferencia exige la nota", async () => {
    stubSalesApi();
    renderApp("/caja");
    const count = await screen.findByRole("form", { name: "Arqueo de la caja" });

    await userEvent.type(within(count).getByLabelText("$20.000"), "2");

    const close = within(count).getByRole("button", { name: /Cerrar caja con \$40\.000/ });
    expect(within(count).getByText("Diferencia").parentElement?.textContent).toBe("Diferenciabaja −$10.000 · faltante");
    expect(close.hasAttribute("disabled")).toBe(true);
    expect(within(count).getByLabelText("Explica la diferencia (obligatorio)")).toBeTruthy();
  });

  it("unos centavos de diferencia también exigen la nota, aunque en pesos se vean $0", async () => {
    stubSalesApi({ "/api/v1/cash/": { ...CASH_OPEN, session: { ...OPEN_SESSION, expected: "50000.40" } } });
    renderApp("/caja");
    const count = await screen.findByRole("form", { name: "Arqueo de la caja" });

    await userEvent.type(within(count).getByLabelText("$50.000"), "1");

    expect(within(count).getByLabelText("Explica la diferencia (obligatorio)")).toBeTruthy();
    expect(
      within(count)
        .getByRole("button", { name: /Cerrar caja con/ })
        .hasAttribute("disabled"),
    ).toBe(true);
    expect(within(count).queryByText("Cuadrada")).toBeNull();
  });

  it("cerrar pide confirmación y envía el conteo por denominación, no el total", async () => {
    const fetch = stubSalesApi({ [CLOSE]: CLOSING });
    renderApp("/caja");
    const count = await screen.findByRole("form", { name: "Arqueo de la caja" });

    await userEvent.type(within(count).getByLabelText("$20.000"), "2");
    await userEvent.type(within(count).getByLabelText("Explica la diferencia (obligatorio)"), "Vueltas");
    await userEvent.click(within(count).getByRole("button", { name: /Cerrar caja con/ }));
    const confirm = await screen.findByRole("dialog", { name: "¿Cerrar la caja?" });
    expect(requestsTo(fetch, CLOSE, "POST")).toHaveLength(0);
    await userEvent.click(within(confirm).getByRole("button", { name: "Sí, cerrar la caja" }));

    await waitFor(() => {
      const body = requestsTo(fetch, CLOSE, "POST")[0]?.body as { bills: unknown[]; coins: string; notes: string };
      expect(body.bills).toContainEqual({ denomination: 20000, count: 2 });
      expect(body).toMatchObject({ coins: "0", notes: "Vueltas" });
      expect(JSON.stringify(body)).not.toMatch(/counted|40000/);
    });
    expect(await screen.findByText(/Caja cerrada con \$40\.000/)).toBeTruthy();
  });

  it("el aviso del cierre se ve aunque, al refrescar, la caja ya no tenga sesión", async () => {
    const fetch = stubSalesApi({ [CLOSE]: CLOSING });
    let closed = false;
    respondAt(fetch, CLOSE, () => {
      closed = true;
      return Promise.resolve(new Response(JSON.stringify(CLOSING)));
    });
    respondAt(fetch, "/api/v1/cash/", () =>
      Promise.resolve(new Response(JSON.stringify(closed ? CASH_CLOSED : CASH_OPEN))),
    );
    renderApp("/caja");
    const count = await screen.findByRole("form", { name: "Arqueo de la caja" });

    await userEvent.type(within(count).getByLabelText("$50.000"), "1");
    await userEvent.click(within(count).getByRole("button", { name: /Cerrar caja con/ }));
    await userEvent.click(await screen.findByRole("button", { name: "Sí, cerrar la caja" }));

    expect(await screen.findByText(/Caja cerrada con \$40\.000/)).toBeTruthy();
    expect(await screen.findByRole("button", { name: "Abrir caja" })).toBeTruthy();
  });

  it("una caja de otro día lo explica, no deja registrar movimientos y ofrece cerrarla", async () => {
    const stale = { ...CASH_OPEN, session: { ...OPEN_SESSION, stale: true } };
    stubSalesApi({ "/api/v1/cash/": { ...stale, actions: { open: false, movement: false, close: true } } });
    renderApp("/caja");

    expect(await screen.findByText(/Esta caja viene de otro día/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Registrar movimiento" })).toBeNull();
    expect(screen.getByRole("link", { name: "Cerrarla ahora" }).getAttribute("href")).toBe("#arqueo");
  });

  it("en todas las sedes pide elegir una", async () => {
    stubSalesApi({ "/api/v1/cash/": { ...CASH_CLOSED, needs_branch: true, branch: null } });
    renderApp("/caja");

    expect(await screen.findByText("Elige una sede para ver su caja.")).toBeTruthy();
  });
});
