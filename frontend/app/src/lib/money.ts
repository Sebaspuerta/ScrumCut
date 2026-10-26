// Vista previa de montos en pantalla (lo que falta por asignar, las vueltas, el contado y la diferencia),
// en centavos enteros: nunca pasa por un float. Al servidor viaja el texto que escribió la persona y los
// totales los calcula el backend; estas cifras solo se muestran.
export const CENTS_PER_PESO = 100;
const DECIMAL = /^(-?)(\d+)(?:\.(\d{1,2}))?$/;

/** "25000.00" → 2500000. Un texto vacío o que no es un monto, null. */
export function toCents(value: string): number | null {
  const match = DECIMAL.exec(value.trim());
  if (!match) return null;
  const [, sign, units = "0", decimals = ""] = match;
  const cents = Number(units) * CENTS_PER_PESO + Number(decimals.padEnd(2, "0"));
  return sign ? -cents : cents;
}

/** Si un monto en texto decimal es exactamente cero: "0.00" sí; "-0.40" no (aunque en pesos se vea $0). */
export function isZeroAmount(value: string): boolean {
  return toCents(value) === 0;
}

/** Si un monto en texto decimal es menor que cero. */
export function isNegativeAmount(value: string): boolean {
  return (toCents(value) ?? 0) < 0;
}

/** 2500000 → "25000.00", el texto decimal que entiende formatCop. */
export function fromCents(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  const absolute = Math.abs(cents);
  const units = Math.trunc(absolute / CENTS_PER_PESO);
  return `${sign}${String(units)}.${String(absolute % CENTS_PER_PESO).padStart(2, "0")}`;
}

/** Lo que escribe la persona en un campo de pesos o de cantidad: solo los dígitos ("25.000" → "25000"). */
export function digitsOnly(text: string): string {
  return text.replace(/\D/g, "");
}

/** La suma de varios montos de la vista previa; uno vacío cuenta como cero. */
export function sumCents(values: readonly string[]): number {
  return values.reduce((total, value) => total + (toCents(value) ?? 0), 0);
}
