import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OWNER_ME, stubOwnerApi } from "../test/fakeApi";
import { renderApp } from "../test/renderApp";
import { applyTheme, effectiveTheme, toggledTheme } from "./theme";

function systemPrefersDark(dark: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: dark,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("tema", () => {
  it("«system» no deja nada en <html>: manda prefers-color-scheme", () => {
    document.documentElement.setAttribute("data-theme", "dark");
    applyTheme("system");
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });

  it.each(["light", "dark"] as const)("«%s» queda en data-theme", (theme) => {
    applyTheme(theme);
    expect(document.documentElement.getAttribute("data-theme")).toBe(theme);
  });

  it("con «system», el que se ve y el contrario siguen al sistema operativo", () => {
    systemPrefersDark(true);
    expect(effectiveTheme("system")).toBe("dark");
    expect(toggledTheme("system")).toBe("light");
    systemPrefersDark(false);
    expect(toggledTheme("system")).toBe("dark");
    expect(toggledTheme("dark")).toBe("light");
  });

  it("el botón cambia al modo oscuro y lo guarda en el servidor con CSRF", async () => {
    const fetch = stubOwnerApi();
    systemPrefersDark(false);
    renderApp();

    await userEvent.click(await screen.findByRole("button", { name: "Usar modo oscuro" }));

    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    await waitFor(() => {
      const patch = fetch.mock.calls.find(([path]) => path === "/api/v1/me/preferences/");
      expect(patch?.[1]?.method).toBe("PATCH");
      expect(patch?.[1]?.body).toBe(JSON.stringify({ theme: "dark" }));
      expect(new Headers(patch?.[1]?.headers).get("X-CSRFToken")).toBe("token-de-prueba");
    });
  });

  it("aplica el tema que la persona guardó en el servidor", async () => {
    stubOwnerApi({ "/api/v1/me/": { ...OWNER_ME, user: { ...OWNER_ME.user, theme: "dark" } } });
    renderApp();

    expect(await screen.findByRole("button", { name: "Usar modo claro" })).toBeDefined();
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
