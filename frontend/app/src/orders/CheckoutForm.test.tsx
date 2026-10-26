import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MAX_LENGTH } from "../lib/fieldLimits";
import { renderApp } from "../test/renderApp";
import { CATALOG, ORDER, ORDER_ID, requestsTo, respondAt, stubSalesApi } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const CHECKOUT = `/api/v1/orders/${ORDER_ID}/checkout/`;

async function openCheckout(fetch = stubSalesApi({ [CHECKOUT]: { order: ORDER, change: "0.00" } })) {
  renderApp(`/comandas?comanda=${ORDER_ID}`);
  const form = await screen.findByRole("form", { name: "Cobrar la comanda" });
  return { fetch, form };
}

const charge = (form: HTMLElement) => within(form).getByRole("button", { name: /Cobrar \$25\.000/ });

describe("cobro de una comanda", () => {
  it("con una sola forma envía el método y lo recibido, nunca el total", async () => {
    const { fetch, form } = await openCheckout();

    await userEvent.type(within(form).getByLabelText("Recibido en efectivo"), "30.000");
    expect(within(form).getByText("$5.000")).toBeTruthy(); // vueltas de la vista previa
    await userEvent.click(charge(form));

    await waitFor(() => {
      expect(requestsTo(fetch, CHECKOUT, "POST")[0]?.body).toEqual({
        parts: [{ method: "efectivo", reference: "" }],
        received: "30000",
        due_date: null,
      });
    });
  });

  it("con una sola forma que no es efectivo pide la referencia opcional y la envía", async () => {
    const { fetch, form } = await openCheckout();
    expect(within(form).queryByLabelText("Referencia del pago")).toBeNull(); // efectivo: sin referencia

    await userEvent.click(within(form).getByRole("radio", { name: "Nequi" }));
    const reference = within(form).getByLabelText("Referencia del pago");
    await userEvent.type(reference, "Nequi 4821");
    await userEvent.click(charge(form));

    expect(reference.getAttribute("maxlength")).toBe(String(MAX_LENGTH.PaymentPartRequest.reference));
    await waitFor(() => {
      expect(requestsTo(fetch, CHECKOUT, "POST")[0]?.body).toEqual({
        parts: [{ method: "nequi", reference: "Nequi 4821" }],
        received: null,
        due_date: null,
      });
    });
  });

  it("el pago dividido muestra lo que falta por asignar y no deja cobrar si se pasa del total", async () => {
    const { form } = await openCheckout();
    await userEvent.click(within(form).getByRole("button", { name: "Dividir el pago" }));

    await userEvent.type(within(form).getByLabelText("Monto de la parte 1"), "10000");
    expect(within(form).getByText("Falta por asignar $15.000.")).toBeTruthy();
    expect(charge(form).hasAttribute("disabled")).toBe(true);

    await userEvent.selectOptions(within(form).getByLabelText("Forma de pago de la parte 2"), "nequi");
    await userEvent.type(within(form).getByLabelText("Monto de la parte 2"), "20000");
    expect(within(form).getByText("Te pasaste del total por $5.000.")).toBeTruthy();
    expect(charge(form).hasAttribute("disabled")).toBe(true);

    await userEvent.clear(within(form).getByLabelText("Monto de la parte 2"));
    await userEvent.type(within(form).getByLabelText("Monto de la parte 2"), "15000");
    expect(within(form).getByText("Asignado todo el total.")).toBeTruthy();
    expect(charge(form).hasAttribute("disabled")).toBe(false);
  });

  it("el número de partes lo pone el servidor", async () => {
    const { form } = await openCheckout(stubSalesApi({ "/api/v1/orders/catalog/": { ...CATALOG, max_parts: 2 } }));

    await userEvent.click(within(form).getByRole("button", { name: "Dividir el pago" }));

    expect(within(form).getByLabelText("Monto de la parte 2")).toBeTruthy();
    expect(within(form).queryByRole("button", { name: "Agregar parte" })).toBeNull();
  });

  it("admite hasta tres partes, una de ellas a fiado con cliente", async () => {
    const { form } = await openCheckout();
    await userEvent.click(within(form).getByRole("button", { name: "Dividir el pago" }));
    await userEvent.click(within(form).getByRole("button", { name: "Agregar parte" }));

    expect(within(form).getByLabelText("Monto de la parte 3")).toBeTruthy();
    expect(within(form).queryByRole("button", { name: "Agregar parte" })).toBeNull();
    const methods = within(within(form).getByLabelText("Forma de pago de la parte 3")).getAllByRole("option");
    expect(methods.map((option) => option.textContent)).toContain("Fiado");
  });

  it("un doble clic en Cobrar envía una sola petición", async () => {
    const fetch = stubSalesApi();
    let release: (response: Response) => void = () => undefined;
    respondAt(fetch, CHECKOUT, () => new Promise((resolve) => (release = resolve)));
    const { form } = await openCheckout(fetch);
    await userEvent.click(within(form).getByRole("radio", { name: "Nequi" }));

    await userEvent.dblClick(charge(form));

    expect(requestsTo(fetch, CHECKOUT, "POST")).toHaveLength(1);
    expect(within(form).getByRole("button", { name: "Cobrando…" }).hasAttribute("disabled")).toBe(true);
    release(new Response(JSON.stringify({ order: ORDER, change: "0.00" })));
    await waitFor(() => {
      expect(requestsTo(fetch, CHECKOUT, "POST")).toHaveLength(1);
    });
  });

  it("muestra el mensaje del servidor si el cobro no se hace", async () => {
    const fetch = stubSalesApi();
    const detail = "No hay una caja abierta en esta sede para recibir el pago.";
    const body = JSON.stringify({ detail, field_errors: {}, code: "no_open_session" });
    respondAt(fetch, CHECKOUT, () => Promise.resolve(new Response(body, { status: 400 })));
    const { form } = await openCheckout(fetch);

    await userEvent.click(within(form).getByRole("radio", { name: "Nequi" }));
    await userEvent.click(charge(form));

    expect((await within(form).findByRole("alert")).textContent).toBe(detail);
  });
});
