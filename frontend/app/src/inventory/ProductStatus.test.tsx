import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CERA, CERA_ID, CERA_PATH, CERA_ROW, PRODUCT_LIST, stubInventoryApi } from "../test/inventoryFixtures";
import { renderApp } from "../test/renderApp";
import { requestsTo } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const ACTIVE = `${CERA_PATH}active/`;
const DELETE = `${CERA_PATH}delete/`;
const INACTIVE = { ...CERA, is_active: false };

async function openProduct(overrides: Record<string, unknown> = {}) {
  const fetch = stubInventoryApi({ [ACTIVE]: CERA, [DELETE]: { id: CERA_ID }, ...overrides });
  renderApp(`/inventario?producto=${CERA_ID}`);
  const panel = await screen.findByRole("region", { name: "Producto" });
  await within(panel).findByRole("heading", { name: "Cera mate" });
  return { fetch, panel };
}

describe("estado del producto", () => {
  it("desactivar pide confirmación; cancelar no envía nada y confirmar lo desactiva", async () => {
    const { fetch, panel } = await openProduct();

    await userEvent.click(within(panel).getByRole("button", { name: "Desactivar" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Cancelar" }));
    expect(requestsTo(fetch, ACTIVE, "POST")).toHaveLength(0);
    await userEvent.click(within(panel).getByRole("button", { name: "Desactivar" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Sí, desactivar" }));

    await waitFor(() => {
      expect(requestsTo(fetch, ACTIVE, "POST")[0]?.body).toEqual({ active: false });
    });
  });

  it("un producto inactivo se ve como tal en la lista y el detalle, y se activa sin confirmación", async () => {
    const list = { ...PRODUCT_LIST, results: [{ ...CERA_ROW, is_active: false }] };
    const { fetch, panel } = await openProduct({ [CERA_PATH]: INACTIVE, "/api/v1/inventory/products/": list });

    expect(within(panel).getByText("Inactivo")).toBeTruthy();
    const rows = screen.getByRole("region", { name: "Lista de productos" });
    expect(within(await within(rows).findByRole("row", { name: /Cera mate/ })).getByText("Inactivo")).toBeTruthy();
    await userEvent.click(within(panel).getByRole("button", { name: "Activar" }));

    await waitFor(() => {
      expect(requestsTo(fetch, ACTIVE, "POST")[0]?.body).toEqual({ active: true });
    });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("borrar pide confirmación y después cierra el panel del producto", async () => {
    const { fetch, panel } = await openProduct();

    await userEvent.click(within(panel).getByRole("button", { name: "Borrar" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Sí, borrar" }));

    await waitFor(() => {
      expect(requestsTo(fetch, DELETE, "POST")).toHaveLength(1);
    });
    expect(await screen.findByText(/Elige un producto de la lista/)).toBeTruthy();
  });

  it.each([
    [{ edit: false, delete: true }, ["Borrar"]],
    [{ edit: true, delete: false }, ["Desactivar"]],
    [{ edit: false, delete: false }, []],
  ])("cada acción sale solo con su permiso (%o)", async (allowed, buttons) => {
    const actions = { ...CERA.actions, ...allowed };
    const { panel } = await openProduct({ [CERA_PATH]: { ...CERA, actions } });

    const shown = ["Desactivar", "Activar", "Borrar"].filter(
      (name) => within(panel).queryByRole("button", { name }) !== null,
    );
    expect(shown).toEqual(buttons);
  });
});
