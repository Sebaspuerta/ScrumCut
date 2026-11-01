import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MAX_LENGTH } from "../lib/fieldLimits";
import { DEBT, DEBT_ID, stubClientsApi } from "../test/clientFixtures";
import { renderApp } from "../test/renderApp";
import { requestsTo, respondAt } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const PAY = `/api/v1/receivables/${DEBT_ID}/pay/`;
const PAID = { ...DEBT, paid: "25000.00", balance: "0.00", status: "pagado", actions: { pay: false } };

async function openPayment(fetch = stubClientsApi({ [PAY]: PAID })) {
  renderApp(`/fiados?fiado=${DEBT_ID}`);
  const form = await screen.findByRole("form", { name: "Registrar abono" });
  return { fetch, form };
}

async function confirmPayment() {
  const dialog = await screen.findByRole("dialog", { name: "¿Registrar el abono?" });
  await userEvent.click(within(dialog).getByRole("button", { name: "Sí, registrar el abono" }));
}

describe("abono a un fiado", () => {
  it("un abono parcial pide confirmación y envía el monto, la referencia, la nota y el saldo visto", async () => {
    const { fetch, form } = await openPayment();
    await userEvent.type(within(form).getByLabelText("Monto del abono"), "10.000");
    expect(within(form).getByText("Saldo después del abono: $15.000")).toBeTruthy();
    await userEvent.click(within(form).getByRole("radio", { name: "Nequi" }));
    await userEvent.type(within(form).getByLabelText("Referencia del pago"), "Nequi 4821");
    await userEvent.type(within(form).getByLabelText("Nota (opcional)"), "Abonó al recoger a su hijo");

    await userEvent.click(within(form).getByRole("button", { name: "Registrar abono de $10.000" }));
    expect(requestsTo(fetch, PAY, "POST")).toHaveLength(0);
    await confirmPayment();

    await waitFor(() => {
      expect(requestsTo(fetch, PAY, "POST")[0]?.body).toEqual({
        amount: "10000",
        method: "nequi",
        reference: "Nequi 4821",
        note: "Abonó al recoger a su hijo",
        expected_balance: "25000.00",
      });
    });
  });

  it("pagar todo usa el saldo del servidor y avisa que el fiado quedó pagado", async () => {
    const { fetch, form } = await openPayment();

    await userEvent.click(within(form).getByRole("button", { name: "Pagar todo" }));
    expect(within(form).getByText("Con este abono el fiado queda pagado.")).toBeTruthy();
    await userEvent.click(within(form).getByRole("button", { name: "Registrar abono de $25.000" }));
    await confirmPayment();

    await waitFor(() => {
      expect(requestsTo(fetch, PAY, "POST")[0]?.body).toMatchObject({
        amount: "25000",
        method: "efectivo",
        reference: "",
      });
    });
    expect(await screen.findByText("Abono de $25.000 registrado: el fiado quedó pagado.")).toBeTruthy();
  });

  it("un monto mayor que el saldo no deja registrar", async () => {
    const { form } = await openPayment();

    await userEvent.type(within(form).getByLabelText("Monto del abono"), "30000");

    expect(within(form).getByText("No puede pasar el saldo de $25.000.")).toBeTruthy();
    expect(within(form).getByRole("button", { name: "Registrar abono" }).hasAttribute("disabled")).toBe(true);
  });

  it("un doble clic al confirmar envía una sola petición", async () => {
    const fetch = stubClientsApi();
    let release: (response: Response) => void = () => undefined;
    respondAt(fetch, PAY, () => new Promise((resolve) => (release = resolve)));
    const { form } = await openPayment(fetch);
    await userEvent.type(within(form).getByLabelText("Monto del abono"), "5000");
    await userEvent.click(within(form).getByRole("button", { name: "Registrar abono de $5.000" }));
    const dialog = await screen.findByRole("dialog", { name: "¿Registrar el abono?" });

    await userEvent.dblClick(within(dialog).getByRole("button", { name: "Sí, registrar el abono" }));

    expect(requestsTo(fetch, PAY, "POST")).toHaveLength(1);
    expect(within(dialog).getByRole("button", { name: "Registrando…" }).hasAttribute("disabled")).toBe(true);
    release(new Response(JSON.stringify(PAID)));
    await waitFor(() => {
      expect(requestsTo(fetch, PAY, "POST")).toHaveLength(1);
    });
  });

  it("muestra el mensaje del servidor si el abono no se hace", async () => {
    const fetch = stubClientsApi();
    const detail = "El saldo del fiado cambió mientras abonabas: revisa el saldo y vuelve a intentarlo.";
    const body = JSON.stringify({ detail, field_errors: {}, code: "stale_balance" });
    respondAt(fetch, PAY, () => Promise.resolve(new Response(body, { status: 400 })));
    const { form } = await openPayment(fetch);
    await userEvent.type(within(form).getByLabelText("Monto del abono"), "5000");
    await userEvent.click(within(form).getByRole("button", { name: "Registrar abono de $5.000" }));
    await confirmPayment();

    const dialog = screen.getByRole("dialog", { name: "¿Registrar el abono?" });
    expect((await within(dialog).findByRole("alert")).textContent).toBe(detail);
  });

  it("la referencia y la nota tienen el largo que acepta el servidor", async () => {
    const { form } = await openPayment();

    await userEvent.click(within(form).getByRole("radio", { name: "Nequi" }));

    expect(within(form).getByLabelText("Referencia del pago").getAttribute("maxlength")).toBe(
      String(MAX_LENGTH.ReceivablePaymentRequest.reference),
    );
    expect(within(form).getByLabelText("Nota (opcional)").getAttribute("maxlength")).toBe(
      String(MAX_LENGTH.ReceivablePaymentRequest.note),
    );
  });

  it("en efectivo no pide referencia y la nota sí va", async () => {
    const { fetch, form } = await openPayment();
    await userEvent.type(within(form).getByLabelText("Monto del abono"), "5000");
    await userEvent.type(within(form).getByLabelText("Nota (opcional)"), "En billetes");

    expect(within(form).queryByLabelText("Referencia del pago")).toBeNull();
    await userEvent.click(within(form).getByRole("button", { name: "Registrar abono de $5.000" }));
    await confirmPayment();

    await waitFor(() => {
      expect(requestsTo(fetch, PAY, "POST")[0]?.body).toMatchObject({ reference: "", note: "En billetes" });
    });
  });

  it("los abonos anteriores muestran su referencia", async () => {
    const payment = {
      id: "p1",
      at: "2026-10-20T15:00:00Z",
      method: "Nequi",
      reference: "4821",
      amount: "5000.00",
      received_by: "Camila Ruiz",
    };
    stubClientsApi({ [`/api/v1/receivables/${DEBT_ID}/`]: { ...DEBT, payments: [payment] } });
    renderApp(`/fiados?fiado=${DEBT_ID}`);

    const history = await screen.findByRole("list", { name: "Abonos anteriores" });

    expect(history.textContent).toContain("Nequi · Ref. 4821 · recibió Camila Ruiz");
  });

  it("en todas las sedes se ve el fiado pero para abonar pide elegir su sede", async () => {
    stubClientsApi({ [`/api/v1/receivables/${DEBT_ID}/`]: { ...DEBT, actions: { pay: false }, needs_branch: true } });
    renderApp(`/fiados?fiado=${DEBT_ID}`);

    expect(await screen.findByText(/Para abonar, elige la sede Centro/)).toBeTruthy();
    expect(screen.queryByRole("form", { name: "Registrar abono" })).toBeNull();
  });
});

describe("lista de fiados", () => {
  it("las pestañas y la búsqueda van en la URL y se las pide al servidor", async () => {
    const fetch = stubClientsApi();
    renderApp("/fiados");
    const list = await screen.findByRole("region", { name: "Lista de fiados" });

    expect((await within(list).findByRole("link", { name: /Pagados en el mes/ })).getAttribute("href")).toBe(
      "/fiados?pestana=pagados",
    );
    await userEvent.type(within(list).getByRole("searchbox", { name: "Buscar cliente" }), "laura{Enter}");

    await waitFor(() => {
      const url = new URL(requestsTo(fetch, "/api/v1/receivables/").at(-1)?.url ?? "", "http://x");
      expect(url.searchParams.get("q")).toBe("laura");
    });
    expect(screen.getByRole("list", { name: "Cartera de la sede" }).textContent).toContain("Por cobrar$25.000");
  });
});
