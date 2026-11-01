import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MAX_LENGTH } from "../lib/fieldLimits";
import { CLIENT_LIST, LAURA, LAURA_ID, stubClientsApi } from "../test/clientFixtures";
import { renderApp } from "../test/renderApp";
import { requestsTo, respondAt } from "../test/salesFixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

const CREATE = "/api/v1/clients/create/";
const EDIT = `/api/v1/clients/${LAURA_ID}/edit/`;

async function openNew(fetch = stubClientsApi({ [CREATE]: LAURA })) {
  renderApp("/clientes?nuevo=1");
  const dialog = await screen.findByRole("dialog", { name: "Nuevo cliente" });
  return { fetch, dialog };
}

const create = (dialog: HTMLElement) => within(dialog).getByRole("button", { name: "Crear cliente" });

describe("formulario de cliente", () => {
  it("no deja crear sin la autorización de la política vigente y la envía al marcarla", async () => {
    const { fetch, dialog } = await openNew();
    await userEvent.type(within(dialog).getByLabelText("Nombre completo"), "Pedro Ríos");
    await userEvent.type(within(dialog).getByLabelText("Celular"), "310 555 1234");

    expect(create(dialog).hasAttribute("disabled")).toBe(true);
    const policy = within(dialog).getByRole("link", { name: "política de tratamiento de datos" });
    expect(policy.getAttribute("href")).toBe(CLIENT_LIST.data_policy?.url);
    expect(within(dialog).getByText(/versión 2026-10/)).toBeTruthy();
    await userEvent.click(within(dialog).getByRole("checkbox", { name: /autoriza el tratamiento/ }));
    await userEvent.click(create(dialog));

    await waitFor(() => {
      expect(requestsTo(fetch, CREATE, "POST")[0]?.body).toEqual({
        full_name: "Pedro Ríos",
        phone: "310 555 1234",
        document: "",
        email: "",
        notes: "",
        consent: true,
        other_person: false,
      });
    });
  });

  it("un posible duplicado por nombre se confirma marcando que es otra persona", async () => {
    const fetch = stubClientsApi();
    const detail = "Ya hay un cliente con ese nombre. Confirma si es otra persona. Con ese nombre: Laura Gómez.";
    let calls = 0;
    respondAt(fetch, CREATE, () => {
      calls += 1;
      const body = calls === 1 ? { detail, code: "possible_duplicate", field_errors: {} } : LAURA;
      return Promise.resolve(new Response(JSON.stringify(body), { status: calls === 1 ? 400 : 201 }));
    });
    const { dialog } = await openNew(fetch);
    await userEvent.type(within(dialog).getByLabelText("Nombre completo"), "Laura Gómez");
    await userEvent.click(within(dialog).getByRole("checkbox", { name: /autoriza el tratamiento/ }));
    await userEvent.click(create(dialog));

    expect((await within(dialog).findByRole("alert")).textContent).toBe(detail);
    await userEvent.click(within(dialog).getByRole("checkbox", { name: "Es otra persona con el mismo nombre" }));
    await userEvent.click(create(dialog));

    await waitFor(() => {
      expect(requestsTo(fetch, CREATE, "POST")[1]?.body).toMatchObject({ other_person: true });
    });
  });

  it("sin política publicada no muestra el formulario", async () => {
    stubClientsApi({ "/api/v1/clients/": { ...CLIENT_LIST, data_policy: null } });
    renderApp("/clientes?nuevo=1");

    const dialog = await screen.findByRole("dialog", { name: "Nuevo cliente" });

    expect(within(dialog).getByText(/No hay una política de tratamiento de datos publicada/)).toBeTruthy();
    expect(within(dialog).queryByLabelText("Nombre completo")).toBeNull();
  });

  it("editar no pide la política, trae el correo y deja celular y cédula vacíos para no cambiarlos", async () => {
    const fetch = stubClientsApi({ [EDIT]: LAURA });
    renderApp(`/clientes?cliente=${LAURA_ID}&editar=1`);
    const dialog = await screen.findByRole("dialog", { name: "Editar a Laura Gómez" });

    expect(within(dialog).queryByRole("checkbox")).toBeNull();
    expect(within(dialog).getByLabelText<HTMLInputElement>("Correo").value).toBe("laura@correo.test");
    await userEvent.click(within(dialog).getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => {
      expect(requestsTo(fetch, EDIT, "POST")[0]?.body).toMatchObject({
        phone: "",
        document: "",
        notes: "Degradado bajo",
      });
    });
  });

  it("los largos máximos de los campos salen del esquema", async () => {
    const { dialog } = await openNew();
    const fields = { "Nombre completo": "full_name", Celular: "phone", Cédula: "document", Correo: "email" } as const;

    for (const [label, field] of Object.entries(fields)) {
      expect(within(dialog).getByLabelText(label).getAttribute("maxlength")).toBe(
        String(MAX_LENGTH.ClientRequest[field]),
      );
    }
  });
});
