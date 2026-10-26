// Largo máximo de los campos de texto de los formularios, por esquema y campo de la petición en openapi.json.
// Solo ayudan al navegador (el servidor valida igual); fieldLimits.test.ts falla si alguno no coincide con el
// esquema o si un formulario escribe un maxLength sin pasar por aquí.
import type { components } from "../api/schema";

type Requests = components["schemas"];

export const MAX_LENGTH = {
  CancelRequest: { reason: 300 },
  CloseCashRequest: { notes: 500 },
  DiscountRequest: { reason: 200 },
  ManualMovementRequest: { description: 200 },
  PaymentPartRequest: { reference: 80 },
} as const satisfies { [Name in keyof Requests]?: { [Field in keyof Requests[Name]]?: number } };
