import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DASHBOARD } from "../test/fakeApi";
import { SalesCalendar } from "./SalesCalendar";

function cells() {
  render(<SalesCalendar calendar={DASHBOARD.calendar} />);
  return within(screen.getByRole("list", { name: "Ventas por día del mes" })).getAllByRole("listitem", {
    hidden: true,
  });
}

describe("calendario de ventas", () => {
  it("el mes empieza en su día de la semana: octubre de 2026 empieza en jueves", () => {
    const week = cells().slice(0, 8);

    expect(week.slice(0, 3).every((cell) => cell.getAttribute("aria-hidden") === "true")).toBe(true);
    expect(week[3]?.getAttribute("aria-label")).toBe("Jueves, 1 de octubre: $125.000 en 5 comandas");
    expect(week[7]?.textContent).toBe("Total$165.000");
  });

  it("un día pasado sin ventas dice «Sin ventas» y hoy va marcado", () => {
    const week = cells();

    expect(week[4]?.textContent).toContain("Sin ventas");
    expect(week[5]?.getAttribute("aria-current")).toBe("date");
  });

  it("los días futuros no muestran cifra ni «Sin ventas»", () => {
    const future = cells()[6];

    expect(future?.getAttribute("aria-label")).toBe("Domingo, 4 de octubre: aún no llega");
    expect(future?.textContent).toBe("4");
  });

  it("el detalle del día trae lo vendido, las comandas y el ticket en pesos", () => {
    const tip = cells()[3]?.textContent ?? "";

    expect(tip).toContain("Vendido $125.000");
    expect(tip).toContain("Comandas 5");
    expect(tip).toContain("Ticket promedio $25.000");
  });
});
