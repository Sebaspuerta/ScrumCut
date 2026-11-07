import type { SubmitEvent } from "react";

import { api } from "../api/client";
import type { Destination, ProductDetail } from "../api/types";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";
import input from "../ui/Input.module.css";
import styles from "./Inventory.module.css";
import { StockFields } from "./StockFields";
import { toTransfer } from "./stockDraft";
import { useStockMove } from "./useStockMove";

interface TransferDialogProps {
  product: ProductDetail;
  onClose: () => void;
}

interface CompareProps {
  product: ProductDetail;
  destination: Destination | undefined;
  quantity: number;
}

/** Lo que hay hoy en el origen y en el destino y cómo quedarían; solo se muestra, el traslado lo hace el servidor. */
function Compare({ product, destination, quantity }: CompareProps) {
  const after = (stock: number, change: number) => (quantity > 0 ? ` → ${String(stock + change)}` : "");
  return (
    <dl className={styles.compare} aria-label="Stock antes del traslado">
      <div>
        <dt>Sale de {product.branch}</dt>
        <dd>
          {product.stock}
          {after(product.stock, -quantity)}
        </dd>
      </div>
      <div>
        <dt>Entra a {destination?.name ?? "la sede de destino"}</dt>
        <dd>{destination ? `${String(destination.stock)}${after(destination.stock, quantity)}` : "—"}</dd>
      </div>
    </dl>
  );
}

/** Lleva unidades de la sede activa a otra sede activa de la barbería; el servidor no deja el origen en negativo. */
export function TransferDialog({ product, onClose }: TransferDialogProps) {
  const { draft, setDraft, mutation, errors } = useStockMove((next, key) =>
    api.post("/api/v1/inventory/products/{public_id}/transfer/", toTransfer(next, key), { public_id: product.id }),
  );
  const destination = product.destinations.find((branch) => branch.id === draft.destination);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    mutation.submit(undefined, onClose);
  };
  const incomplete = draft.destination === "" || draft.quantity === "" || draft.reason.trim() === "";
  return (
    <FormDialog
      title={`Traslado de ${product.name}`}
      subtitle={`Desde la sede ${product.branch ?? ""}`}
      onClose={onClose}
    >
      <form className={form.form} onSubmit={submit} aria-label="Traslado de stock">
        <Field label="Sede de destino" error={errors.fields.destination}>
          {(control) => (
            <select
              {...control}
              className={input.input}
              required
              value={draft.destination}
              onChange={(event) => {
                setDraft({ ...draft, destination: event.target.value });
              }}
            >
              <option value="">Elige la sede</option>
              {product.destinations.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.name}
                </option>
              ))}
            </select>
          )}
        </Field>
        <StockFields
          draft={draft}
          errors={errors}
          onChange={setDraft}
          quantityLabel="Unidades que se trasladan"
          reasonHint="Por ejemplo: reparto entre sedes."
          request="TransferRequest"
        />
        <Compare product={product} destination={destination} quantity={Number(draft.quantity || "0")} />
        <FormAlert message={errors.detail} />
        <div className={form.actions}>
          <Button kind="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending || incomplete}>
            {mutation.isPending ? "Trasladando…" : "Confirmar traslado"}
          </Button>
        </div>
      </form>
    </FormDialog>
  );
}
