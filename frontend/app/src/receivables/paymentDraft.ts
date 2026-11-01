// El abono mientras se llena. Al servidor viaja el monto tal como lo escribió la persona y el saldo que vio; que
// no pase el saldo y vaya a la caja de la sede de origen lo decide add_payment. La vista previa (el saldo después
// del abono) solo se muestra, en centavos enteros.
import type { ReceivableDetail, ReceivablePaymentRequest } from "../api/types";
import { formatCop } from "../lib/format";
import { fromCents, toCents } from "../lib/money";
import { CASH_METHOD } from "../lib/paymentMethods";

export interface PaymentDraft {
  amount: string;
  method: string;
  reference: string;
  note: string;
}

export interface PaymentPreview {
  valid: boolean;
  text: string;
}

export function initialPayment(receivable: ReceivableDetail): PaymentDraft {
  return { amount: "", method: receivable.methods[0]?.value ?? CASH_METHOD, reference: "", note: "" };
}

/** Lo que queda después del abono, o por qué todavía no se puede registrar. */
export function preview(draft: PaymentDraft, balance: string): PaymentPreview {
  const amount = toCents(draft.amount) ?? 0;
  const after = (toCents(balance) ?? 0) - amount;
  if (amount <= 0) return { valid: false, text: "Escribe cuánto abona el cliente." };
  if (after < 0) return { valid: false, text: `No puede pasar el saldo de ${formatCop(balance)}.` };
  if (after === 0) return { valid: true, text: "Con este abono el fiado queda pagado." };
  return { valid: true, text: `Saldo después del abono: ${formatCop(fromCents(after))}` };
}

/** La referencia solo va con los medios que no son efectivo (Nequi 4821); la nota, con cualquiera. */
export function toRequest(draft: PaymentDraft, balance: string): ReceivablePaymentRequest {
  const reference = draft.method === CASH_METHOD ? "" : draft.reference.trim();
  return { amount: draft.amount, method: draft.method, reference, note: draft.note.trim(), expected_balance: balance };
}
