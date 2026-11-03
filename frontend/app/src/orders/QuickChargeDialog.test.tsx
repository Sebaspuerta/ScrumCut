import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { OrderDetail } from "../api/types";
import { MAX_LENGTH } from "../lib/fieldLimits";
import { NAVIGATION } from "../test/fakeApi";
import { renderApp } from "../test/renderApp";
import { ANA_ID, CORTE_ID, ORDER, requestsTo, respondAt, stubSalesApi } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const QUICK = "/api/v1/orders/quick-charge/";
const CHARGED: OrderDetail = { ...ORDER, number: 148, status: "cerrada", client: null, editable: false };

async function openDialog(fetch = stubSalesApi({ [QUICK]: CHARGED })) {
  renderApp("/comandas?cobro=1");
  const dialog = await screen.findByRole("dialog", { name: "Cobro rápido" });
  const form = await within(dialog).findByRole("form", { name: "Cobro rápido" });
  return { fetch, dialog, form };
}

async function pickCorte(form: HTMLElement) {
  await userEvent.selectOptions(within(form).getByLabelText("Servicio o producto"), `servicio:${CORTE_ID}`);
}

const chargeButton = (form: HTMLElement) => within(form).getByRole("button", { name: /^Cobra/ });
const sentKeys = (fetch: ReturnType<typeof stubSalesApi>) =>
  requestsTo(fetch, QUICK, "POST").map((request) => (request.body as { request_key: string }).request_key);

describe("cobro rápido", () => {
  it("envía el ítem, el barbero y la forma de pago con su llave; nunca precio, cliente ni fiado", async () => {
    const { fetch, form } = await openDialog();

    await pickCorte(form);
    await userEvent.click(within(form).getByRole("radio", { name: "Nequi" }));
    const reference = within(form).getByLabelText("Referencia del pago");
    await userEvent.type(reference, "N-4821");
    await userEvent.click(within(form).getByRole("button", { name: "Cobrar $25.000" }));

    await waitFor(() => {
      expect(requestsTo(fetch, QUICK, "POST")[0]?.body).toEqual({
        request_key: expect.stringMatching(/^[0-9a-f-]{36}$/) as unknown,
        barber: ANA_ID,
        service: CORTE_ID,
        product: null,
        method: "nequi",
        reference: "N-4821",
      });
    });
    expect(JSON.stringify(requestsTo(fetch, QUICK, "POST")[0]?.body)).not.toMatch(/price|total|client|fiado/);
    expect(reference.getAttribute("maxlength")).toBe(String(MAX_LENGTH.QuickChargeRequest.reference));
    expect(within(form).queryByRole("radio", { name: "Fiado" })).toBeNull();
  });

  it("confirma el cobro y queda listo para el siguiente con una llave nueva", async () => {
    const { fetch, form } = await openDialog();
    await pickCorte(form);
    await userEvent.click(chargeButton(form));

    expect((await within(form).findByRole("status")).textContent).toBe("Comanda #148 cobrada: $25.000.");
    expect(within(form).getByLabelText<HTMLSelectElement>("Servicio o producto").value).toBe("");
    await pickCorte(form);
    await userEvent.click(chargeButton(form));

    await waitFor(() => {
      expect(sentKeys(fetch)).toHaveLength(2);
    });
    expect(new Set(sentKeys(fetch)).size).toBe(2);
  });

  it("un doble clic en Cobrar envía una sola petición", async () => {
    const fetch = stubSalesApi();
    let release: (response: Response) => void = () => undefined;
    respondAt(fetch, QUICK, () => new Promise((resolve) => (release = resolve)));
    const { form } = await openDialog(fetch);
    await pickCorte(form);

    await userEvent.dblClick(chargeButton(form));

    expect(requestsTo(fetch, QUICK, "POST")).toHaveLength(1);
    expect(within(form).getByRole("button", { name: "Cobrando…" }).hasAttribute("disabled")).toBe(true);
    release(new Response(JSON.stringify(CHARGED), { status: 201 }));
    await waitFor(() => {
      expect(requestsTo(fetch, QUICK, "POST")).toHaveLength(1);
    });
  });

  it("si la caja viene de otro día lo explica y el reintento conserva la llave", async () => {
    const fetch = stubSalesApi();
    const detail = "La caja viene de otro día: ciérrala y abre la de hoy.";
    const body = JSON.stringify({ detail, field_errors: {}, code: "stale_session" });
    respondAt(fetch, QUICK, () => Promise.resolve(new Response(body, { status: 400 })));
    const { form } = await openDialog(fetch);
    await pickCorte(form);

    await userEvent.click(chargeButton(form));
    expect((await within(form).findByRole("alert")).textContent).toBe(detail);
    await userEvent.click(chargeButton(form));

    await waitFor(() => {
      expect(sentKeys(fetch)).toHaveLength(2);
    });
    expect(new Set(sentKeys(fetch)).size).toBe(1);
  });

  it.each([
    [
      "el botón de Comandas",
      async () => {
        await userEvent.click(await screen.findByRole("button", { name: "Cobro rápido" }));
      },
      "/comandas",
    ],
    [
      "el menú + Nuevo",
      async () => {
        await userEvent.click(await screen.findByRole("button", { name: /Nuevo/ }));
        await userEvent.click(screen.getByRole("link", { name: "Cobro rápido" }));
      },
      "/",
    ],
    [
      "la paleta Ctrl K",
      async () => {
        await screen.findByRole("navigation", { name: "Navegación principal" });
        await userEvent.keyboard("{Control>}k{/Control}");
        await userEvent.type(screen.getByRole("combobox"), "cobro rapido{Enter}");
      },
      "/",
    ],
  ])("%s abre el cobro rápido de React", async (_, open, start) => {
    const action = {
      label: "Cobro rápido",
      icon: "banknote",
      app_path: "/comandas?cobro=1",
      status: "enlace" as const,
    };
    const navigation = { ...NAVIGATION, new_actions: [action] };
    stubSalesApi({ "/api/v1/navigation/": navigation });
    renderApp(start);

    await open();

    expect(await screen.findByRole("dialog", { name: "Cobro rápido" })).toBeTruthy();
  });
});
