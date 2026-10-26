import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NAVIGATION } from "../test/fakeApi";
import { renderApp } from "../test/renderApp";
import { ANA_ID, CATALOG, CORTE_ID, ORDER, requestsTo, respondAt, stubSalesApi } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const CREATE = "/api/v1/orders/create/";
const LAURA = { id: "c1", name: "Laura Gómez", phone: "300 *** 4567" };

async function openForm(fetch = stubSalesApi({ [CREATE]: ORDER, "/api/v1/clients/search/": [LAURA] })) {
  renderApp("/comandas?nueva=1");
  const dialog = await screen.findByRole("dialog", { name: "Nueva comanda" });
  await within(dialog).findByRole("form", { name: "Abrir la comanda" });
  return { fetch, dialog };
}

async function addCorte(dialog: HTMLElement) {
  await userEvent.selectOptions(within(dialog).getByLabelText("Servicio o producto"), `servicio:${CORTE_ID}`);
  await userEvent.click(within(dialog).getByRole("button", { name: "Agregar a la comanda" }));
}

describe("formulario de comanda", () => {
  it("abre la comanda con el cliente, el barbero y sus líneas, sin enviar precios", async () => {
    const { fetch, dialog } = await openForm();

    await userEvent.type(within(dialog).getByRole("searchbox"), "laura{Enter}");
    await userEvent.click(await within(dialog).findByRole("button", { name: /Laura Gómez/ }));
    await userEvent.selectOptions(within(dialog).getByLabelText("Barbero"), ANA_ID);
    await addCorte(dialog);
    await userEvent.click(within(dialog).getByRole("button", { name: "Abrir comanda" }));

    await waitFor(() => {
      expect(requestsTo(fetch, CREATE, "POST")[0]?.body).toEqual({
        client: "c1",
        barber: ANA_ID,
        lines: [{ service: CORTE_ID, product: null, quantity: 1, barber: null }],
      });
    });
    expect(JSON.stringify(requestsTo(fetch, CREATE, "POST")[0]?.body)).not.toMatch(/price|total/);
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Nueva comanda" })).toBeNull();
    });
  });

  it("muestra el precio vigente de la sede y deja quitar una línea antes de abrir", async () => {
    const { dialog } = await openForm();

    expect(within(dialog).getByLabelText("Cantidad").getAttribute("max")).toBe(String(CATALOG.max_quantity));
    expect(within(dialog).getByRole("option", { name: "Corte · $25.000" })).toBeTruthy();
    expect(within(dialog).getByRole("option", { name: "Cera · $20.000 · 5 en stock" })).toBeTruthy();
    await addCorte(dialog);
    await userEvent.click(within(dialog).getByRole("button", { name: "Quitar Corte" }));

    expect(within(dialog).queryByRole("list", { name: "Líneas para abrir la comanda" })).toBeNull();
  });

  it("muestra junto a cada campo el error de validación del servidor", async () => {
    const fetch = stubSalesApi();
    const body = {
      detail: "Revisa los datos enviados.",
      field_errors: { barber: ["El barbero no trabaja en esta sede."] },
      code: null,
    };
    respondAt(fetch, CREATE, () => Promise.resolve(new Response(JSON.stringify(body), { status: 400 })));
    const { dialog } = await openForm(fetch);

    await userEvent.selectOptions(within(dialog).getByLabelText("Barbero"), ANA_ID);
    await userEvent.click(within(dialog).getByRole("button", { name: "Abrir comanda" }));

    const barber = within(dialog).getByLabelText("Barbero");
    expect(await within(dialog).findByText("El barbero no trabaja en esta sede.")).toBeTruthy();
    expect(barber.getAttribute("aria-invalid")).toBe("true");
    expect(barber.getAttribute("aria-describedby")).toBeTruthy();
  });

  it("Esc cierra el formulario", async () => {
    await openForm();

    await userEvent.keyboard("{Escape}");

    expect(screen.queryByRole("dialog", { name: "Nueva comanda" })).toBeNull();
  });

  it.each([
    [
      "el menú + Nuevo",
      async () => {
        await userEvent.click(await screen.findByRole("button", { name: /Nuevo/ }));
        await userEvent.click(screen.getByRole("link", { name: "Nueva comanda" }));
      },
    ],
    [
      "la paleta Ctrl K",
      async () => {
        await screen.findByRole("navigation", { name: "Navegación principal" });
        await userEvent.keyboard("{Control>}k{/Control}");
        await userEvent.type(screen.getByRole("combobox"), "nueva comanda{Enter}");
      },
    ],
  ])("%s abre el formulario de React", async (_, open) => {
    const action = { label: "Nueva comanda", icon: "receipt", url: "/comandas/nueva/", status: "enlace" as const };
    const navigation = { ...NAVIGATION, new_actions: [{ ...action, app_path: "/comandas?nueva=1" }] };
    stubSalesApi({ "/api/v1/navigation/": navigation });
    renderApp("/");

    await open();

    expect(await screen.findByRole("dialog", { name: "Nueva comanda" })).toBeTruthy();
  });
});
