import { describe, expect, it } from "vitest";

import {
  clock,
  countOf,
  dayLabel,
  formatCop,
  formatVariation,
  longDate,
  monthLabel,
  openedSince,
  outflowCop,
  shortDate,
  signedCop,
  weekdayIndex,
  zonedDate,
} from "./format";
import shared from "./format-cases.json";

const cases = shared as {
  cop: [string | number | null, string][];
  short_date: [string, string][];
  day_label: [string, string][];
  month_label: [string, string][];
  clock: [string, string, string][];
  opened_since: [string, string, string, string][];
};

// Los mismos casos que prueba el backend con apps/core/formatting.py (tests/frontend/test_formatting.py).
describe("formato colombiano", () => {
  it.each(cases.cop)("formatCop(%j) es %s", (value, expected) => {
    expect(formatCop(value)).toBe(expected);
  });

  it.each(cases.short_date)("shortDate(%s) es %s", (value, expected) => {
    expect(shortDate(value)).toBe(expected);
  });

  it.each(cases.day_label)("dayLabel(%s) es %s", (value, expected) => {
    expect(dayLabel(value)).toBe(expected);
  });

  it.each(cases.month_label)("monthLabel(%s) es %s", (value, expected) => {
    expect(monthLabel(value)).toBe(expected);
  });

  it.each(cases.clock)("clock(%s, %s) es %s", (value, timeZone, expected) => {
    expect(clock(value, timeZone)).toBe(expected);
  });

  it.each(cases.opened_since)("openedSince(%s, %s, %s) es %s", (value, today, timeZone, expected) => {
    expect(openedSince(value, today, timeZone)).toBe(expected);
  });

  it("rechaza un valor que no es un decimal", () => {
    expect(() => formatCop("12,5")).toThrow(RangeError);
  });

  it("fecha larga para el encabezado y el detalle del día", () => {
    expect(longDate("2026-10-22", true)).toBe("Jueves, 22 de octubre de 2026");
    expect(longDate("2026-10-01")).toBe("Jueves, 1 de octubre");
    expect(weekdayIndex("2026-10-19")).toBe(0);
  });

  it("el día de un instante se lee en la zona de la barbería", () => {
    expect(zonedDate("2026-10-23T03:00:00Z", "America/Bogota")).toBe("2026-10-22");
  });

  it("variación con signo y coma decimal; la flecha es un ícono aparte, sin rojos", () => {
    expect(formatVariation("12.4")).toBe("+12,4 %");
    expect(formatVariation("-3.1")).toBe("−3,1 %");
    expect(formatVariation(null)).toBe("—");
  });

  it("un monto que suma o resta lleva su signo", () => {
    expect(signedCop("5000.00")).toBe("+$5.000");
    expect(signedCop("-8000.00")).toBe("−$8.000");
    expect(signedCop("0.00")).toBe("$0");
    expect(outflowCop("8000.00")).toBe("−$8.000");
    expect(outflowCop("0.00")).toBe("$0");
    expect(countOf(1, "pago", "pagos")).toBe("1 pago");
    expect(countOf(0, "pago", "pagos")).toBe("0 pagos");
  });
});
