import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { stubOwnerApi } from "../test/fakeApi";
import { FakeFailure, NETWORK_DOWN } from "../test/stubApi";
import { renderApp } from "../test/renderApp";
import { ScreenErrorBoundary } from "./ScreenErrorBoundary";

const DASHBOARD_PATH = "/api/v1/dashboard/";
const OFFLINE_RETRIES_MS = 6000; // la app reintenta dos veces una falla de red antes de avisar

function stubLocation() {
  const assign = vi.fn<(url: string) => void>();
  vi.stubGlobal("location", { assign, pathname: "/app/caja", search: "?tipo=gasto" });
  return assign;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("errores de la app", () => {
  it("una ruta que no existe muestra la 404 dentro del marco", async () => {
    stubOwnerApi();
    renderApp("/no-existe");

    expect(await screen.findByRole("heading", { name: "Esta página no existe" })).toBeDefined();
    expect(screen.getByRole("navigation", { name: "Navegación principal" })).toBeDefined();
  });

  it("sin sesión manda al login de Django con la ruta para volver", async () => {
    const assign = stubLocation();
    stubOwnerApi({
      [DASHBOARD_PATH]: new FakeFailure(403, { detail: "Inicia sesión.", code: "not_authenticated", field_errors: {} }),
    });
    renderApp("/");

    await vi.waitFor(() => {
      expect(assign).toHaveBeenCalledWith("/cuenta/login/?next=%2Fapp%2Fcaja%3Ftipo%3Dgasto");
    });
  });

  it("sin permiso dice que no tiene acceso, no ofrece reintentar y no manda al login", async () => {
    const assign = stubLocation();
    const denied = { detail: "No tienes permiso para esta acción.", code: "permission_denied", field_errors: {} };
    stubOwnerApi({ [DASHBOARD_PATH]: new FakeFailure(403, denied) });
    renderApp("/");

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("No tienes acceso a esta sección.");
    expect(within(alert).queryByRole("button", { name: "Reintentar" })).toBeNull();
    expect(assign).not.toHaveBeenCalled();
  });

  it("con demasiadas peticiones muestra el aviso de la API y deja reintentar", async () => {
    const throttled = { detail: "Demasiadas solicitudes. Intenta de nuevo en un momento.", code: "throttled" };
    const fetch = stubOwnerApi({ [DASHBOARD_PATH]: new FakeFailure(429, { ...throttled, field_errors: {} }) });
    renderApp("/");

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain(throttled.detail);
    const before = fetch.mock.calls.length;
    await userEvent.click(within(alert).getByRole("button", { name: "Reintentar" }));
    expect(fetch.mock.calls.length).toBeGreaterThan(before);
  });

  it(
    "sin conexión avisa y deja reintentar",
    async () => {
      stubOwnerApi({ [DASHBOARD_PATH]: NETWORK_DOWN });
      renderApp("/");

      const alert = await screen.findByRole("alert", {}, { timeout: OFFLINE_RETRIES_MS });
      expect(alert.textContent).toContain("No hay conexión con ScrumCut");
      expect(within(alert).getByRole("button", { name: "Reintentar" })).toBeDefined();
    },
    OFFLINE_RETRIES_MS + 2000,
  );
});

function Fragile({ broken }: { broken: boolean }) {
  if (broken) throw new Error("detalle interno: TypeError en la línea 42");
  return <p>Pantalla en orden</p>;
}

function BreakOnce() {
  const [broken, setBroken] = useState(true);
  return (
    <>
      <button
        type="button"
        onClick={() => {
          setBroken(false);
        }}
      >
        Arreglar
      </button>
      <ScreenErrorBoundary>
        <Fragile broken={broken} />
      </ScreenErrorBoundary>
    </>
  );
}

describe("fallo inesperado de una pantalla", () => {
  it("muestra el aviso con Reintentar y Volver al inicio, sin la pila, y reintentar vuelve a pintarla", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined); // React registra el error atrapado
    render(
      <MemoryRouter>
        <BreakOnce />
      </MemoryRouter>,
    );

    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("Algo salió mal en esta pantalla.");
    expect(alert.textContent).not.toContain("detalle interno");
    expect(within(alert).getByRole("link", { name: "Volver al inicio" }).getAttribute("href")).toBe("/");

    await userEvent.click(screen.getByRole("button", { name: "Arreglar" }));
    await userEvent.click(within(alert).getByRole("button", { name: "Reintentar" }));
    expect(screen.getByText("Pantalla en orden")).toBeDefined();
  });
});
