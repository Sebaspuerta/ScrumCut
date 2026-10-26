// Una línea mientras se escribe: el ítem va como "servicio:<id>" o "producto:<id>" en el selector. Nunca
// lleva precio: el servidor lo toma del catálogo de la sede.
import type { NewLine, OrderCatalog } from "../api/types";

export interface LineDraft {
  item: string;
  barber: string;
  quantity: string;
}

export const EMPTY_LINE: LineDraft = { item: "", barber: "", quantity: "1" };
export const SERVICE = "servicio";
export const PRODUCT = "producto";

export function itemValue(kind: typeof SERVICE | typeof PRODUCT, id: string): string {
  return `${kind}:${id}`;
}

/** Lo que se envía a la API: el servicio o el producto, la cantidad y el barbero (vacío, el de la comanda). */
export function toNewLine(draft: LineDraft): NewLine {
  const [kind, id = null] = draft.item.split(":");
  return {
    service: kind === SERVICE ? id : null,
    product: kind === PRODUCT ? id : null,
    quantity: Number(draft.quantity),
    barber: draft.barber || null,
  };
}

/** El nombre del ítem elegido, para mostrarlo en la lista del formulario. */
export function itemName(catalog: OrderCatalog, item: string): string {
  const [kind, id] = item.split(":");
  const options = kind === SERVICE ? catalog.services : catalog.products;
  return options.find((option) => option.id === id)?.name ?? "";
}
