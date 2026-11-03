// El cobro rápido mientras se llena: el ítem va como "servicio:<id>" o "producto:<id>" (lineDraft.ts) y nunca lleva
// precio, cantidad, cliente ni fiado: el precio es el de la sede y lo demás no existe en el cobro rápido (regla 17).
import type { OrderCatalog, QuickChargeRequest } from "../api/types";
import { CASH_METHOD } from "../lib/paymentMethods";
import { EMPTY_LINE, PRODUCT, SERVICE, toNewLine } from "./lineDraft";

export interface QuickChargeDraft {
  item: string;
  barber: string;
  method: string;
  reference: string;
}

/** Listo en pocos toques: el primer barbero y la primera forma de pago del servidor ya elegidos. */
export function initialQuickCharge(catalog: OrderCatalog): QuickChargeDraft {
  return { item: "", barber: catalog.barbers[0]?.id ?? "", method: catalog.methods[0]?.value ?? "", reference: "" };
}

/** Después de cobrar queda listo para el siguiente: el mismo barbero y la misma forma de pago, sin ítem. */
export function nextQuickCharge(draft: QuickChargeDraft): QuickChargeDraft {
  return { ...draft, item: "", reference: "" };
}

/** La referencia solo se anota en un pago que no es en efectivo. */
export function takesReference(draft: QuickChargeDraft): boolean {
  return draft.method !== CASH_METHOD;
}

/** El precio de la sede del ítem elegido, solo para mostrarlo en el botón; el servidor no lo recibe. */
export function shownPrice(catalog: OrderCatalog, item: string): string | null {
  const [kind, id] = item.split(":");
  const options = kind === SERVICE ? catalog.services : kind === PRODUCT ? catalog.products : [];
  return options.find((option) => option.id === id)?.price ?? null;
}

export function toQuickChargeRequest(draft: QuickChargeDraft, requestKey: string): QuickChargeRequest {
  const { service, product } = toNewLine({ ...EMPTY_LINE, item: draft.item });
  return {
    request_key: requestKey,
    barber: draft.barber,
    service: service ?? null,
    product: product ?? null,
    method: draft.method,
    reference: takesReference(draft) ? draft.reference : "",
  };
}
