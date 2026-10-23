import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NAVIGATION, OWNER_ME, stubApi, stubOwnerApi } from "../test/fakeApi";
import { renderApp } from "../test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("marco de la app", () => {
  it("arma la barra superior y la lateral con me y navigation, y el tablero en /app/", async () => {
    stubOwnerApi();
    renderApp();

    expect(await screen.findByRole("heading", { name: "Resumen ejecutivo" })).toBeDefined();
    const banner = screen.getByRole("banner");
    expect(within(banner).getByText("Barbería Demo")).toBeDefined();
    expect(within(banner).getByText("SCRUMCUT")).toBeDefined();
    expect(await within(banner).findByRole("button", { name: "Notificaciones: 3 sin leer" })).toBeDefined();
    const nav = screen.getByRole("navigation", { name: "Navegación principal" });
    expect(within(nav).getByRole("link", { name: "Tablero" }).getAttribute("aria-current")).toBe("page");
    expect(within(nav).getByRole("link", { name: "Comandas" }).getAttribute("href")).toBe("/comandas/");
    expect(within(nav).queryByRole("link", { name: /Agenda/ })).toBeNull();
    expect(within(nav).getByText("Pronto")).toBeDefined();
  });

  it("los cierres de sesión son formularios POST a Django con el token CSRF", async () => {
    stubOwnerApi();
    renderApp();

    await userEvent.click(await screen.findByRole("button", { name: "Cuenta de Laura Peña" }));
    const logout = await screen.findByRole("button", { name: "Cerrar sesión" });
    await vi.waitFor(() => {
      expect(logout.hasAttribute("disabled")).toBe(false);
    });
    const form = logout.closest("form");

    expect(form?.getAttribute("method")).toBe("post");
    expect(form?.getAttribute("action")).toBe("/cuenta/logout/");
    expect(form?.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")?.value).toBe("token-de-prueba");
  });

  it("«+ Nuevo» se abre con la tecla N con las acciones del rol", async () => {
    stubOwnerApi();
    renderApp();
    await screen.findByRole("button", { name: /Nuevo/ });

    await userEvent.keyboard("n");

    expect(screen.getByRole("link", { name: "Nueva comanda" }).getAttribute("href")).toBe("/comandas/nueva/");
  });

  it("sin reportes.ver, el tablero manda al tablero actual en vez de pedir datos que no le tocan", async () => {
    const fetch = stubApi({
      "/api/v1/me/": { ...OWNER_ME, permissions: [] },
      "/api/v1/navigation/": { ...NAVIGATION, unread_alerts: null },
    });
    renderApp();

    expect(await screen.findByText(/es para quien ve los reportes/)).toBeDefined();
    expect(fetch.mock.calls.some(([path]) => typeof path === "string" && path.startsWith("/api/v1/dashboard/"))).toBe(
      false,
    );
  });

  it("sin barbería activa lo dice y no pide la navegación", async () => {
    const fetch = stubApi({ "/api/v1/me/": { ...OWNER_ME, barbershop: null, role: null, branch: null } });
    renderApp();

    expect(await screen.findByText(/no tiene una barbería activa/)).toBeDefined();
    expect(fetch.mock.calls.map((call) => call[0])).toEqual(["/api/v1/me/"]);
  });

  it("si me falla muestra el error con la opción de reintentar", async () => {
    stubApi({});
    renderApp();

    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeDefined();
  });
});
