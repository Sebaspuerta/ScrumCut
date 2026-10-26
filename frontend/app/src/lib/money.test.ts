import { describe, expect, it } from "vitest";

import { fromCents, isNegativeAmount, isZeroAmount, sumCents, toCents } from "./money";

describe("montos de la vista previa", () => {
  it("convierte el texto decimal de la API a centavos enteros y de vuelta", () => {
    expect(toCents("25000.00")).toBe(2500000);
    expect(toCents("-8000.5")).toBe(-800050);
    expect(toCents("12,5")).toBeNull();
    expect(fromCents(-800050)).toBe("-8000.50");
    expect(sumCents(["10000", "", "5000.25"])).toBe(1500025);
  });

  it("cero es exactamente cero: unos centavos de diferencia no lo son, aunque en pesos se vean $0", () => {
    expect(isZeroAmount("0.00")).toBe(true);
    expect(isZeroAmount("-0.00")).toBe(true);
    expect(isZeroAmount("-0.40")).toBe(false);
    expect(isZeroAmount("0.01")).toBe(false);
  });

  it("negativo es menor que cero", () => {
    expect(isNegativeAmount("-0.40")).toBe(true);
    expect(isNegativeAmount("0.00")).toBe(false);
    expect(isNegativeAmount("5000.00")).toBe(false);
  });
});
