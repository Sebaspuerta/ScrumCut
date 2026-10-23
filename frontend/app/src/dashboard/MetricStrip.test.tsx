import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { DASHBOARD } from "../test/fakeApi";
import { MetricStrip } from "./MetricStrip";

function metric(label: string): string {
  const item = within(screen.getByRole("list", { name: "Indicadores" }))
    .getAllByRole("listitem")
    .find((node) => node.textContent.startsWith(label));
  return item?.textContent ?? "";
}

describe("indicadores", () => {
  beforeEach(() => {
    render(<MetricStrip data={DASHBOARD} />);
  });

  it("las cifras en pesos llevan punto de miles y sin decimales", () => {
    expect(metric("Ingresos de hoy")).toContain("$3.440.000");
    expect(metric("Esperado en caja")).toContain("$1.284.000");
  });

  it("lo positivo sube con flecha y signo; lo negativo baja, sin rojos", () => {
    expect(metric("Ingresos de hoy")).toContain("▴ +12,4 % vs. sábado anterior a esta hora");
    expect(metric("Ticket promedio")).toContain("▾ −3,1 % vs. período anterior");
  });

  it("sin con qué comparar lo dice en texto", () => {
    expect(metric("Comandas cerradas")).toContain("8 abiertas ahora");
  });

  it("los fiados muestran el saldo, los vencidos y los clientes", () => {
    const text = metric("Fiados pendientes");
    expect(text).toContain("$682.000");
    expect(text).toContain("4 vencidos · 5 clientes");
  });
});
