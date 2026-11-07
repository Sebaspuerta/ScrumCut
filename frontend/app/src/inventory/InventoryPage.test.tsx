import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CERA, CERA_ID, CERA_PATH, CUIDADO_ID, stubInventoryApi } from "../test/inventoryFixtures";
import { renderApp } from "../test/renderApp";
import { requestsTo, respondAt } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const LIST = "/api/v1/inventory/products/";
const CREATE = "/api/v1/inventory/products/create/";
const UPLOAD = `${CERA_PATH}photo/upload/`;
const EDIT = `${CERA_PATH}edit/`;
const NOT_AN_IMAGE = "El archivo no es una imagen válida.";
const lastListQuery = (fetch: ReturnType<typeof stubInventoryApi>) =>
  new URL(requestsTo(fetch, LIST).at(-1)?.url ?? "", "http://x").searchParams;

describe("inventario", () => {
  it("lista el stock y el precio de la sede con el aviso de stock bajo, y el aviso enlaza al producto", async () => {
    stubInventoryApi();
    renderApp("/inventario");
    const list = await screen.findByRole("region", { name: "Lista de productos" });

    const row = (await within(list).findByRole("link", { name: /Cera mate/ })).closest("tr");
    expect(row?.textContent).toContain("$22.000");
    expect(within(row as HTMLElement).getByText("Stock bajo")).toBeTruthy();
    const alerts = await screen.findByRole("region", { name: "Stock bajo" });
    const alertLink = within(alerts).getByRole("link", { name: /Cera mate/ });
    expect(alertLink.getAttribute("href")).toBe(`/inventario?producto=${CERA_ID}`);
  });

  it("los filtros de búsqueda, categoría, tipo y estado van en la URL y se los pide al servidor", async () => {
    const fetch = stubInventoryApi();
    renderApp("/inventario");
    const list = await screen.findByRole("region", { name: "Lista de productos" });

    await userEvent.type(within(list).getByRole("searchbox", { name: "Buscar producto" }), "cera{Enter}");
    await userEvent.selectOptions(await within(list).findByRole("combobox", { name: "Categoría" }), CUIDADO_ID);
    await userEvent.selectOptions(within(list).getByRole("combobox", { name: "Tipo" }), "venta");
    await userEvent.selectOptions(within(list).getByRole("combobox", { name: "Estado" }), "todos");

    await waitFor(() => {
      expect(Object.fromEntries(lastListQuery(fetch))).toEqual({
        q: "cera",
        categoria: CUIDADO_ID,
        tipo: "venta",
        estado: "todos",
      });
    });
  });

  it("la URL con filtros y página se le pasa tal cual a la API al entrar", async () => {
    const fetch = stubInventoryApi();
    renderApp("/inventario?categoria=sin&estado=inactivos&pagina=2");

    await screen.findByRole("region", { name: "Lista de productos" });

    expect(Object.fromEntries(lastListQuery(fetch))).toEqual({ categoria: "sin", estado: "inactivos", page: "2" });
  });

  it("el detalle muestra el precio de la sede, el stock por sede y los movimientos", async () => {
    stubInventoryApi();
    renderApp(`/inventario?producto=${CERA_ID}`);
    const panel = await screen.findByRole("region", { name: "Producto" });

    expect(await within(panel).findByRole("heading", { name: "Cera mate" })).toBeTruthy();
    expect(within(panel).getByText("Precio en Centro").nextElementSibling?.textContent).toBe("$22.000");
    expect(within(panel).getByText("Inventario inicial", { exact: false })).toBeTruthy();
    expect(within(panel).getByRole("group", { name: "Mover stock" })).toBeTruthy();
  });

  it("en «todas» no ofrece mover stock: pide elegir una sede", async () => {
    stubInventoryApi({ [CERA_PATH]: { ...CERA, actions: { ...CERA.actions, adjust: false }, needs_branch: true } });
    renderApp(`/inventario?producto=${CERA_ID}`);

    expect(await screen.findByText("Elige una sede en la barra superior para mover el stock.")).toBeTruthy();
    expect(screen.queryByRole("group", { name: "Mover stock" })).toBeNull();
  });

  it("crea el producto y después sube su foto, con la vista previa antes de guardar", async () => {
    const fetch = stubInventoryApi({ [CREATE]: CERA, [UPLOAD]: CERA });
    renderApp("/inventario?nuevo=1");
    const dialog = await screen.findByRole("dialog", { name: "Nuevo producto" });

    await userEvent.type(within(dialog).getByLabelText("Nombre"), "Cera mate");
    await userEvent.type(within(dialog).getByLabelText("Costo de compra"), "8.000");
    await userEvent.type(within(dialog).getByLabelText("Precio de venta"), "20000");
    await userEvent.type(within(dialog).getByLabelText("Stock inicial"), "5");
    const photo = new File(["png"], "cera.png", { type: "image/png" });
    await userEvent.upload(within(dialog).getByLabelText("Foto"), photo);
    expect(await within(dialog).findByRole("img", { name: "Vista previa de la foto" })).toBeTruthy();
    await userEvent.click(within(dialog).getByRole("button", { name: "Crear producto" }));

    await waitFor(() => {
      expect(fetch.mock.calls.some(([input]) => input === UPLOAD)).toBe(true);
    });
    expect(requestsTo(fetch, CREATE, "POST")[0]?.body).toMatchObject({
      name: "Cera mate",
      purchase_cost: "8000",
      sale_price: "20000",
      initial_stock: 5,
      category: null,
      product_type: "venta",
    });
    const sent = fetch.mock.calls.find(([input]) => input === UPLOAD)?.[1]?.body;
    expect(sent instanceof FormData ? sent.get("photo") : null).toBe(photo);
  });

  it("la foto se elige con el botón «Elegir foto», muestra su vista previa y «Quitar» la descarta", async () => {
    stubInventoryApi();
    renderApp("/inventario?nuevo=1");
    const dialog = await screen.findByRole("dialog", { name: "Nuevo producto" });
    const input = within(dialog).getByLabelText("Elegir foto");

    expect(input.getAttribute("type")).toBe("file");
    await userEvent.upload(input, new File(["png"], "cera.png", { type: "image/png" }));
    expect(await within(dialog).findByRole("img", { name: "Vista previa de la foto" })).toBeTruthy();
    expect(within(dialog).getByText("Cambiar foto")).toBeTruthy();
    await userEvent.click(within(dialog).getByRole("button", { name: "Quitar" }));

    expect(within(dialog).queryByRole("img", { name: "Vista previa de la foto" })).toBeNull();
    expect(within(dialog).getByText("Elegir foto")).toBeTruthy();
    expect((input as HTMLInputElement).value).toBe("");
  });

  it("si el servidor rechaza la foto, lo dice en el campo y el reintento edita el producto ya creado", async () => {
    const invalid = { detail: "Revisa los datos enviados.", code: "invalid", field_errors: { photo: [NOT_AN_IMAGE] } };
    const fetch = stubInventoryApi({ [CREATE]: CERA, [EDIT]: CERA });
    respondAt(fetch, UPLOAD, () => Promise.resolve(new Response(JSON.stringify(invalid), { status: 400 })));
    renderApp("/inventario?nuevo=1");
    const dialog = await screen.findByRole("dialog", { name: "Nuevo producto" });

    await userEvent.type(within(dialog).getByLabelText("Nombre"), "Cera mate");
    await userEvent.upload(within(dialog).getByLabelText("Foto"), new File(["x"], "x.png", { type: "image/png" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Crear producto" }));
    expect(await within(dialog).findByText(NOT_AN_IMAGE)).toBeTruthy();
    await userEvent.click(within(dialog).getByRole("button", { name: "Crear producto" }));

    await waitFor(() => {
      expect(requestsTo(fetch, EDIT, "POST")).toHaveLength(1);
    });
    expect(requestsTo(fetch, CREATE, "POST")).toHaveLength(1);
  });
});
