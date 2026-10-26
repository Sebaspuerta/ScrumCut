// El cobro mientras se llena. Lo que se envía son las formas de pago y los montos tal como los escribió la
// persona; que sumen el total, las vueltas y el cupo de fiado los decide el servidor (checkout_order). La
// vista previa (lo que falta por asignar, las vueltas) solo se muestra, en centavos enteros.
import type { CheckoutRequest } from "../api/types";
import { sumCents, toCents } from "../lib/money";

export const CASH = "efectivo";
export const CREDIT = "fiado";

export interface PartDraft {
  method: string;
  amount: string;
  reference: string;
}

export interface CheckoutDraft {
  split: boolean;
  method: string;
  reference: string;
  received: string;
  dueDate: string;
  parts: PartDraft[];
}

export function emptyPart(method: string): PartDraft {
  return { method, amount: "", reference: "" };
}

export function initialDraft(method: string): CheckoutDraft {
  return { split: false, method, reference: "", received: "", dueDate: "", parts: [emptyPart(method)] };
}

/** «Dividir el pago» empieza con la forma elegida y una parte más; volver deja una sola forma. */
export function toggleSplit(draft: CheckoutDraft): CheckoutDraft {
  if (draft.split) return { ...draft, split: false };
  return { ...draft, split: true, parts: [emptyPart(draft.method), emptyPart("")] };
}

function methods(draft: CheckoutDraft): string[] {
  return draft.split ? draft.parts.map((part) => part.method) : [draft.method];
}

export function usesCash(draft: CheckoutDraft): boolean {
  return methods(draft).includes(CASH);
}

/** Con una sola forma de pago que no es efectivo ni fiado se puede anotar su referencia. */
export function takesReference(draft: CheckoutDraft): boolean {
  return !draft.split && draft.method !== CASH && draft.method !== CREDIT;
}

export function usesCredit(draft: CheckoutDraft): boolean {
  return methods(draft).includes(CREDIT);
}

function parts(draft: CheckoutDraft): CheckoutRequest["parts"] {
  if (!draft.split) return [{ method: draft.method, reference: draft.reference }];
  return draft.parts.map((part) => ({ method: part.method, amount: part.amount || null, reference: part.reference }));
}

export function toRequest(draft: CheckoutDraft): CheckoutRequest {
  return {
    parts: parts(draft),
    received: usesCash(draft) ? draft.received || null : null,
    due_date: usesCredit(draft) ? draft.dueDate || null : null,
  };
}

/** Lo que falta por asignar en el pago dividido (negativo: se pasó del total); en una sola forma, null. */
export function remainingCents(draft: CheckoutDraft, total: string): number | null {
  if (!draft.split) return null;
  return (toCents(total) ?? 0) - sumCents(draft.parts.map((part) => part.amount));
}

/** La parte en efectivo: todo el total con una sola forma, o la suma de las partes en efectivo. */
export function cashCents(draft: CheckoutDraft, total: string): number {
  if (!draft.split) return draft.method === CASH ? (toCents(total) ?? 0) : 0;
  return sumCents(draft.parts.filter((part) => part.method === CASH).map((part) => part.amount));
}

/** Las vueltas de la vista previa (negativo: falta recibir); sin lo recibido, null. */
export function changeCents(draft: CheckoutDraft, total: string): number | null {
  const received = toCents(draft.received);
  return received === null ? null : received - cashCents(draft, total);
}
