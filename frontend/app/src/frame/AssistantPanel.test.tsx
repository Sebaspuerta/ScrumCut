import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { stubOwnerApi } from "../test/fakeApi";
import { renderApp } from "../test/renderApp";

// AGENTS.md: el asistente se muestra sin funcionalidad hasta que el backend esté completo.
describe("asistente", () => {
  it("se muestra sin funcionalidad: «Disponible pronto», el campo deshabilitado y nada que enviar", async () => {
    const fetch = stubOwnerApi();
    renderApp();
    await userEvent.click(await screen.findByRole("button", { name: /Asistente/ }));
    const before = fetch.mock.calls.length;

    const panel = screen.getByRole("region", { name: "Asistente" });
    const field = within(panel).getByRole("textbox", { name: "Pregunta para el asistente" });

    expect(within(panel).getByText("Disponible pronto")).toBeDefined();
    expect(within(panel).getByText("El asistente estará disponible pronto.")).toBeDefined();
    expect(field.hasAttribute("disabled")).toBe(true);
    expect(panel.querySelector("form")).toBeNull();
    expect(
      within(panel)
        .getAllByRole("button")
        .map((button) => button.getAttribute("aria-label")),
    ).toEqual(["Cerrar el asistente"]);
    await userEvent.type(field, "¿Cuánto vendí hoy?");
    expect((field as HTMLInputElement).value).toBe("");
    expect(fetch.mock.calls.length).toBe(before);
  });
});
