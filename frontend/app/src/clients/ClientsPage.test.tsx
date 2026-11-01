import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CLIENT_LIST, DEBT_ID, LAURA_ID, LAURA_ROW, stubClientsApi } from "../test/clientFixtures";
import { renderApp } from "../test/renderApp";
import { requestsTo } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const LIST = "/api/v1/clients/";
const lastListQuery = (fetch: ReturnType<typeof stubClientsApi>) =>
  new URL(requestsTo(fetch, LIST).at(-1)?.url ?? "", "http://x").searchParams;

describe("clientes", () => {
  it("los filtros de búsqueda, nivel y orden van en la URL y se los pide al servidor", async () => {
    const fetch = stubClientsApi();
    renderApp("/clientes");
    const list = await screen.findByRole("region", { name: "Lista de clientes" });

    await userEvent.type(within(list).getByRole("searchbox", { name: "Buscar cliente" }), "laura{Enter}");
    await waitFor(() => {
      expect(lastListQuery(fetch).get("q")).toBe("laura");
    });
    await userEvent.click(await within(list).findByRole("button", { name: /Deudor/ }));
    await waitFor(() => {
      expect(lastListQuery(fetch).get("nivel")).toBe("debtor");
    });
    await userEvent.selectOptions(within(list).getByRole("combobox", { name: "Ordenar por" }), "deuda");

    await waitFor(() => {
      expect(Object.fromEntries(lastListQuery(fetch))).toEqual({ q: "laura", nivel: "debtor", orden: "deuda" });
    });
  });

  it("la URL con filtros y página se le pasa tal cual a la API al entrar", async () => {
    const fetch = stubClientsApi();
    renderApp("/clientes?q=ana&nivel=vip&pagina=2");

    await screen.findByRole("region", { name: "Lista de clientes" });

    expect(Object.fromEntries(lastListQuery(fetch))).toEqual({ q: "ana", nivel: "vip", page: "2" });
  });

  it("un cliente de otra sede encontrado por búsqueda sale sin cifras de esa sede", async () => {
    const elsewhere = { ...LAURA_ROW, has_activity: false, level: null, level_label: "Sin visitas en la sede" };
    stubClientsApi({ [LIST]: { ...CLIENT_LIST, results: [{ ...elsewhere, visits: null, debt: null }] } });
    renderApp("/clientes?q=laura");

    const row = (await screen.findByRole("link", { name: /Laura Gómez/ })).closest("tr");

    expect(row?.textContent).toContain("Sin visitas en la sede");
    expect(row?.textContent).not.toContain("$25.000");
  });

  it("la ficha muestra el nivel en la sede, la deuda con su fiado y el celular enmascarado", async () => {
    stubClientsApi();
    renderApp(`/clientes?cliente=${LAURA_ID}`);

    const card = await screen.findByRole("region", { name: "Laura Gómez" });

    expect(within(card).getByText(/300 \*\*\* 4567/)).toBeTruthy();
    expect(within(card).getByRole("progressbar", { name: "Avance al siguiente nivel" })).toBeTruthy();
    expect(within(card).getByRole("link", { name: "Ver fiado y abonar" }).getAttribute("href")).toBe(
      `/fiados?fiado=${DEBT_ID}`,
    );
    expect(within(card).getByRole("button", { name: "Nueva comanda para Laura" })).toBeTruthy();
  });

  it("sin clientes muestra el estado vacío", async () => {
    stubClientsApi({ [LIST]: { ...CLIENT_LIST, results: [], count: 0 } });
    renderApp("/clientes");

    expect(await screen.findByText("Ningún cliente coincide. Revisa la búsqueda o crea uno nuevo.")).toBeTruthy();
  });

  it("si la lista no carga, muestra el error con reintento", async () => {
    stubClientsApi({ [LIST]: undefined }); // un 4xx no se reintenta (queryClient.ts)
    renderApp("/clientes");

    expect((await screen.findByRole("alert")).textContent).toContain("No pudimos cargar los clientes.");
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeTruthy();
  });
});
