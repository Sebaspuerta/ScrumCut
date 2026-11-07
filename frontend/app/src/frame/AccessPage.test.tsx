import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Access, Me } from "../api/types";
import { OWNER_ME, stubOwnerApi } from "../test/fakeApi";
import { renderApp } from "../test/renderApp";

function withoutBarbershop(access: Access): Me {
  return { ...OWNER_ME, access, barbershop: null, role: null, permissions: [], branch: null };
}

async function showAccess(access: Access) {
  stubOwnerApi({ "/api/v1/me/": withoutBarbershop(access) });
  renderApp("/");
  return screen.findByRole("heading", { level: 1 });
}

describe("pérdida de acceso", () => {
  it.each([
    [{ status: "no_barbershop", barbershop: null, support_email: null }, "Tu cuenta no tiene una barbería"],
    [
      { status: "membership_inactive", barbershop: "Barbería Sur", support_email: null },
      "Ya no tienes acceso a Barbería Sur",
    ],
    [{ status: "several_barbershops", barbershop: null, support_email: null }, "Tienes acceso a varias barberías"],
    [
      { status: "barbershop_closed", barbershop: "Barbería Sur", support_email: null },
      "Barbería Sur cerró su cuenta en ScrumCut",
    ],
  ] satisfies [Access, string][])("%j muestra su pantalla con Cerrar sesión", async (access, title) => {
    expect((await showAccess(access)).textContent).toBe(title);

    const logout = screen.getByRole("button", { name: "Cerrar sesión" });
    const form = logout.closest("form");
    expect(form?.getAttribute("action")).toBe("/cuenta/logout/");
    expect(form?.getAttribute("method")).toBe("post");
    expect(screen.queryByRole("navigation", { name: "Navegación principal" })).toBeNull();
  });

  it("al dueño de una barbería suspendida le da el contacto de ScrumTech que entrega la API", async () => {
    const access: Access = {
      status: "barbershop_suspended",
      barbershop: "Barbería Sur",
      support_email: "ayuda@example.com",
    };

    expect((await showAccess(access)).textContent).toBe("El acceso a Barbería Sur está suspendido");
    expect(screen.getByText(/Escríbenos a ayuda@example.com/)).toBeDefined();
  });

  it("a los demás les dice que hablen con el dueño", async () => {
    await showAccess({ status: "barbershop_suspended", barbershop: "Barbería Sur", support_email: null });

    expect(screen.getByText(/Habla con el dueño de la barbería/)).toBeDefined();
  });
});

describe("textos de pérdida de acceso", () => {
  it("con varias barberías explica que aún no puede elegir y da el contacto de ScrumTech", async () => {
    await showAccess({ status: "several_barbershops", barbershop: null, support_email: "ayuda@example.com" });

    expect(
      screen.getByText(
        "Tu cuenta tiene acceso a varias barberías y todavía no puedes elegir con cuál trabajar. " +
          "Escríbenos a ayuda@example.com y lo resolvemos.",
      ),
    ).toBeDefined();
  });

  it("con varias barberías y sin contacto configurado no ofrece escribir", async () => {
    await showAccess({ status: "several_barbershops", barbershop: null, support_email: null });

    expect(
      screen.getByText("Tu cuenta tiene acceso a varias barberías y todavía no puedes elegir con cuál trabajar."),
    ).toBeDefined();
  });
});
