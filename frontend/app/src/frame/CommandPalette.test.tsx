import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { stubOwnerApi } from "../test/fakeApi";
import { renderApp } from "../test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
});

async function openPalette() {
  stubOwnerApi();
  renderApp();
  await screen.findByRole("navigation", { name: "Navegación principal" });
  await screen.findByRole("link", { name: "Comandas" });
  await userEvent.keyboard("{Control>}k{/Control}");
  return screen.getByRole("dialog", { name: "Buscar en ScrumCut" });
}

const selected = (dialog: HTMLElement) =>
  within(dialog)
    .getAllByRole("option")
    .find((option) => option.getAttribute("aria-selected") === "true");

describe("paleta de comandos", () => {
  it("abre con Ctrl K con el foco en la búsqueda y cierra con Esc", async () => {
    const dialog = await openPalette();

    expect(within(dialog).getByRole("combobox")).toBe(document.activeElement);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("ofrece la navegación y las acciones del rol, y la búsqueda de clientes como Próximamente", async () => {
    const dialog = await openPalette();
    const labels = within(dialog)
      .getAllByRole("option")
      .map((option) => option.textContent);

    expect(labels).toEqual(expect.arrayContaining([expect.stringContaining("Nueva comanda")]));
    expect(labels).toEqual(expect.arrayContaining([expect.stringContaining("Tablero")]));
    const upcoming = within(dialog).getByRole("option", { name: /Buscar cliente/ });
    expect(upcoming.getAttribute("aria-disabled")).toBe("true");
    expect(labels.some((label) => label.includes("Agenda"))).toBe(false); // sin pantalla: no se ofrece
  });

  it("se maneja con el teclado: las flechas saltan lo que no se puede abrir y dan la vuelta", async () => {
    const dialog = await openPalette();
    const first = selected(dialog);

    await userEvent.keyboard("{ArrowDown}");
    const second = selected(dialog);
    await userEvent.keyboard("{ArrowUp}");

    expect(second).not.toBe(first);
    expect(selected(dialog)).toBe(first);
    await userEvent.keyboard("{ArrowUp}");
    expect(selected(dialog)?.getAttribute("aria-disabled")).toBe("false");
  });

  it("filtra sin mayúsculas ni tildes y Enter abre la pantalla elegida", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { assign, pathname: "/app/", search: "" });
    const dialog = await openPalette();

    await userEvent.type(within(dialog).getByRole("combobox"), "COMÁNDAS");
    await userEvent.keyboard("{Enter}");

    expect(assign).toHaveBeenCalledWith("/comandas/");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
