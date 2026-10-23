import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CASHIER_ME, stubOwnerApi } from "../test/fakeApi";
import { renderApp } from "../test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("selector de sede", () => {
  it("con una sola sede y sin «todas» es solo texto", async () => {
    stubOwnerApi({ "/api/v1/me/": CASHIER_ME });
    renderApp();

    expect(await screen.findByText("Sede: Centro")).toBeDefined();
    expect(screen.queryByRole("button", { name: /Cambiar de sede/ })).toBeNull();
  });

  it("muestra las sedes del servidor con la actual marcada, «Todas las sedes» y Gestionar sedes", async () => {
    stubOwnerApi();
    renderApp();

    await userEvent.click(await screen.findByRole("button", { name: "Sede: Centro. Cambiar de sede" }));
    const menu = screen.getByRole("list", { name: "Sedes" });

    expect(within(menu).getByRole("button", { name: /Todas las sedes/ })).toBeDefined();
    expect(within(menu).getByRole("button", { name: "Centro" }).getAttribute("aria-current")).toBe("true");
    expect(within(menu).getByText("Gestionar sedes")).toBeDefined();
  });

  it("cambiar de sede es un POST a la API con su token CSRF, y Esc cierra el menú", async () => {
    const fetch = stubOwnerApi({
      "/api/v1/branch/": { mode: "una", current_label: "Norte", options: [], can_view_all: true, can_manage: true },
    });
    renderApp();
    const trigger = await screen.findByRole("button", { name: "Sede: Centro. Cambiar de sede" });

    await userEvent.click(trigger);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("list", { name: "Sedes" })).toBeNull();
    expect(document.activeElement).toBe(trigger);

    await userEvent.click(trigger);
    await userEvent.click(screen.getByRole("button", { name: "Norte" }));

    await waitFor(() => {
      const post = fetch.mock.calls.find(([path]) => path === "/api/v1/branch/");
      expect(post?.[1]?.body).toBe(JSON.stringify({ sede: "norte" }));
      expect(new Headers(post?.[1]?.headers).get("X-CSRFToken")).toBe("token-de-prueba");
    });
  });
});
