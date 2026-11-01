import { screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderApp } from "../test/renderApp";
import { ORDER, ORDER_ID, stubSalesApi } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const CREDITED = {
  ...ORDER,
  status: "cerrada",
  actions: { edit: false, discount: false, checkout: false, cancel: false },
  receivable: { id: "f1", balance: "25000.00", status: "pendiente" },
};

describe("enlaces de la comanda", () => {
  it("lleva a la ficha del cliente y al fiado que generó", async () => {
    stubSalesApi({ [`/api/v1/orders/${ORDER_ID}/`]: CREDITED });
    renderApp(`/comandas?comanda=${ORDER_ID}`);

    const panel = await screen.findByRole("region", { name: "Laura Gómez" });

    expect(within(panel).getByRole("link", { name: "Laura Gómez" }).getAttribute("href")).toBe("/clientes?cliente=c1");
    expect(within(panel).getByRole("link", { name: "Ver el fiado y sus abonos" }).getAttribute("href")).toBe(
      "/fiados?fiado=f1",
    );
  });
});
