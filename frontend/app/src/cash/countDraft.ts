// El arqueo mientras se cuenta. Al servidor viaja cuántos billetes hay de cada denominación y las monedas: él
// suma el contado (CloseSessionForm) y calcula la diferencia. Aquí solo se muestra la vista previa.
import { CENTS_PER_PESO, fromCents, toCents } from "../lib/money";

export interface CountDraft {
  bills: Partial<Record<number, string>>;
  coins: string;
  notes: string;
}

export const EMPTY_COUNT: CountDraft = { bills: {}, coins: "", notes: "" };

function billCount(draft: CountDraft, denomination: number): number {
  return Number(draft.bills[denomination] ?? "") || 0;
}

function billCents(draft: CountDraft, denomination: number): number {
  return denomination * CENTS_PER_PESO * billCount(draft, denomination);
}

/** Lo que suman los billetes de una denominación, como texto decimal para mostrarlo. */
export function billSubtotal(draft: CountDraft, denomination: number): string {
  return fromCents(billCents(draft, denomination));
}

/** El contado de la vista previa, en centavos: billetes por su denominación más las monedas. */
export function countedCents(draft: CountDraft, denominations: readonly number[]): number {
  const bills = denominations.reduce((total, denomination) => total + billCents(draft, denomination), 0);
  return bills + (toCents(draft.coins) ?? 0);
}

/** Contado − esperado, como texto decimal para mostrarlo con signo y flecha. */
export function previewDifference(draft: CountDraft, denominations: readonly number[], expected: string): string {
  return fromCents(countedCents(draft, denominations) - (toCents(expected) ?? 0));
}

export function toCloseRequest(draft: CountDraft, denominations: readonly number[]) {
  return {
    bills: denominations.map((denomination) => ({ denomination, count: billCount(draft, denomination) })),
    coins: draft.coins || "0",
    notes: draft.notes,
  };
}
