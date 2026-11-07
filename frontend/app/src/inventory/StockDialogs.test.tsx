import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CERA, CERA_ID, CERA_PATH, NORTE_ID, stubInventoryApi } from "../test/inventoryFixtures";
import { renderApp } from "../test/renderApp";
import { requestsTo, respondAt } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const ENTRY = `${CERA_PATH}entry/`;
const ADJUSTMENT = `${CERA_PATH}adjustment/`;
const TRANSFER = `${CERA_PATH}transfer/`;
const UUID = /^[0-9a-f-]{36}$/;

async function openMove(move: string, overrides: Record<string, unknown> = {}) {
  const fetch = stubInventoryApi({ [ENTRY]: CERA, [ADJUSTMENT]: CERA, [TRANSFER]: CERA, ...overrides });
  renderApp(`/inventario?producto=${CERA_ID}&mover=${move}`);
  const dialog = await screen.findByRole("dialog");
  return { fetch, dialog };
}

async function fill(dialog: HTMLElement, quantityLabel: string, quantity: string, reason: string) {
  await userEvent.type(within(dialog).getByLabelText(quantityLabel), quantity);
  await userEvent.type(within(dialog).getByLabelText("Motivo"), reason);
}

describe("movimientos de stock", () => {
  it("la entrada manda la cantidad, el costo y el motivo con su llave", async () => {
    const { fetch, dialog } = await openMove("entrada");
    await fill(dialog, "Unidades que entran", "3", "Compra");
    await userEvent.type(within(dialog).getByLabelText("Costo unitario"), "7.500");
    await userEvent.click(within(dialog).getByRole("button", { name: "Registrar entrada" }));

    await waitFor(() => {
      expect(requestsTo(fetch, ENTRY, "POST")[0]?.body).toEqual({
        request_key: expect.stringMatching(UUID) as unknown,
        quantity: 3,
        reason: "Compra",
        unit_cost: "7500",
      });
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
  });

  it("el ajuste resta por defecto y suma si se elige", async () => {
    const { fetch, dialog } = await openMove("ajuste");
    await fill(dialog, "Unidades", "2", "Merma");
    await userEvent.click(within(dialog).getByRole("button", { name: "Registrar ajuste" }));

    await waitFor(() => {
      expect(requestsTo(fetch, ADJUSTMENT, "POST")[0]?.body).toMatchObject({ quantity: -2, reason: "Merma" });
    });
  });

  it("el traslado muestra el stock de origen y de destino antes de confirmar", async () => {
    const { fetch, dialog } = await openMove("traslado");
    await userEvent.selectOptions(within(dialog).getByLabelText("Sede de destino"), NORTE_ID);
    await fill(dialog, "Unidades que se trasladan", "2", "Reparto");

    const compare = within(dialog).getByLabelText("Stock antes del traslado");
    expect(compare.textContent).toContain("Sale de Centro5 → 3");
    expect(compare.textContent).toContain("Entra a Norte3 → 5");
    await userEvent.click(within(dialog).getByRole("button", { name: "Confirmar traslado" }));

    await waitFor(() => {
      expect(requestsTo(fetch, TRANSFER, "POST")[0]?.body).toMatchObject({
        destination: NORTE_ID,
        quantity: 2,
        reason: "Reparto",
      });
    });
  });

  it("un doble clic manda una sola petición", async () => {
    const { fetch, dialog } = await openMove("entrada");
    let finish: (response: Response) => void = () => undefined;
    respondAt(fetch, ENTRY, () => new Promise((resolve) => (finish = resolve)));
    await fill(dialog, "Unidades que entran", "1", "Compra");
    const submit = within(dialog).getByRole("button", { name: "Registrar entrada" });

    await userEvent.dblClick(submit);

    expect(requestsTo(fetch, ENTRY, "POST")).toHaveLength(1);
    expect(within(dialog).getByRole("button", { name: "Registrando…" }).hasAttribute("disabled")).toBe(true);
    finish(new Response(JSON.stringify(CERA)));
  });

  it("si la red corta la entrada, el reintento lleva la misma llave", async () => {
    const { fetch, dialog } = await openMove("entrada");
    let calls = 0;
    respondAt(fetch, ENTRY, () => {
      calls += 1;
      return calls === 1
        ? Promise.reject(new TypeError("Failed to fetch"))
        : Promise.resolve(new Response(JSON.stringify(CERA)));
    });
    await fill(dialog, "Unidades que entran", "1", "Compra");
    await userEvent.click(within(dialog).getByRole("button", { name: "Registrar entrada" }));
    await within(dialog).findByRole("alert");
    await userEvent.click(within(dialog).getByRole("button", { name: "Registrar entrada" }));

    await waitFor(() => {
      expect(requestsTo(fetch, ENTRY, "POST")).toHaveLength(2);
    });
    const [first, retry] = requestsTo(fetch, ENTRY, "POST");
    expect(retry?.body).toEqual(first?.body);
  });
});
