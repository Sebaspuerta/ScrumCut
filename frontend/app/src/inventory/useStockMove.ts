import { useState } from "react";

import { formErrors } from "../api/errors";
import type { ProductDetail } from "../api/types";
import { useWriteMutation } from "../hooks/useWriteMutation";
import { BLANK_STOCK, newRequestKey, type StockDraft } from "./stockDraft";

/** Un movimiento de stock mientras su diálogo está abierto: el borrador, su llave (la misma en cada reintento) y
 * la escritura, que ignora un segundo envío mientras el primero sigue en curso. */
export function useStockMove(send: (draft: StockDraft, requestKey: string) => Promise<ProductDetail>) {
  const [draft, setDraft] = useState<StockDraft>(BLANK_STOCK);
  const [requestKey] = useState(newRequestKey);
  const mutation = useWriteMutation(() => send(draft, requestKey));
  return { draft, setDraft, mutation, errors: formErrors(mutation.error) };
}
