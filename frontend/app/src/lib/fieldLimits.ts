// Largo máximo de los campos de texto y valor máximo de los enteros de los formularios, por esquema y campo de la
// petición en openapi.json (maxLength y maximum). Solo ayudan al navegador (el servidor valida igual);
// fieldLimits.test.ts falla si alguno no coincide con el esquema o si un formulario escribe un maxLength o un max
// sin pasar por aquí.
import type { components } from "../api/schema";

type Requests = components["schemas"];
type Limits = { [Name in keyof Requests]?: { [Field in keyof Requests[Name]]?: number } };

export const MAX_LENGTH = {
  AdjustmentRequest: { reason: 200 },
  CancelRequest: { reason: 300 },
  CategoryRequest: { name: 80 },
  ClientRequest: { full_name: 120, phone: 20, document: 20, email: 254, notes: 1000 },
  ClientUpdateRequest: { full_name: 120, phone: 20, document: 20, email: 254, notes: 1000 },
  CloseCashRequest: { notes: 500 },
  DiscountRequest: { reason: 200 },
  EntryRequest: { reason: 200 },
  ManualMovementRequest: { description: 200 },
  PaymentPartRequest: { reference: 80 },
  ProductCreateRequest: { name: 120, supplier: 120 },
  ProductRequest: { name: 120, supplier: 120 },
  QuickChargeRequest: { reference: 80 },
  ReceivablePaymentRequest: { reference: 80, note: 200 },
  TransferRequest: { reason: 200 },
} as const satisfies Limits;

/** El tope de unidades de inventario (`MAX_QUANTITY` en el backend), tal como lo publica el esquema. */
export const MAX_VALUE = {
  AdjustmentRequest: { quantity: 1000000 },
  EntryRequest: { quantity: 1000000 },
  ProductCreateRequest: { minimum_stock: 1000000, initial_stock: 1000000 },
  ProductRequest: { minimum_stock: 1000000 },
  TransferRequest: { quantity: 1000000 },
} as const satisfies Limits;
