// Entradas, ajustes y traslados mientras se llenan. Cada intento lleva su llave (request_key): la misma en cada
// reintento, así un doble envío no mueve el stock dos veces; el servidor valida cantidades, motivo y sede.
import type { AdjustmentRequest, EntryRequest, TransferRequest } from "../api/types";

/** La llave de un intento: la misma mientras el diálogo siga abierto con los mismos datos. */
export const newRequestKey = () => crypto.randomUUID();

export interface StockDraft {
  quantity: string;
  reason: string;
  unit_cost: string;
  /** Ajuste: resta (una merma, lo más común) o suma. */
  direction: "restar" | "sumar";
  destination: string;
}

export const BLANK_STOCK: StockDraft = {
  quantity: "",
  reason: "",
  unit_cost: "",
  direction: "restar",
  destination: "",
};

const whole = (text: string) => Number(text || "0");

export function toEntry(draft: StockDraft, requestKey: string): EntryRequest {
  return {
    request_key: requestKey,
    quantity: whole(draft.quantity),
    reason: draft.reason,
    unit_cost: draft.unit_cost === "" ? null : draft.unit_cost,
  };
}

export function toAdjustment(draft: StockDraft, requestKey: string): AdjustmentRequest {
  const sign = draft.direction === "restar" ? -1 : 1;
  return { request_key: requestKey, quantity: sign * whole(draft.quantity), reason: draft.reason };
}

export function toTransfer(draft: StockDraft, requestKey: string): TransferRequest {
  return {
    request_key: requestKey,
    destination: draft.destination,
    quantity: whole(draft.quantity),
    reason: draft.reason,
  };
}
