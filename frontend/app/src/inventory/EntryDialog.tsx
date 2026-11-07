import type { SubmitEvent } from "react";

import { api } from "../api/client";
import type { ProductDetail } from "../api/types";
import { cx } from "../lib/cx";
import { formatCop } from "../lib/format";
import { digitsOnly } from "../lib/money";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";
import input from "../ui/Input.module.css";
import { StockFields } from "./StockFields";
import { toEntry } from "./stockDraft";
import { useStockMove } from "./useStockMove";

interface EntryDialogProps {
  product: ProductDetail;
  onClose: () => void;
}

/** Regla 33: unidades que llegan a la sede, con su costo unitario (sin él, el del producto) y el motivo. */
export function EntryDialog({ product, onClose }: EntryDialogProps) {
  const { draft, setDraft, mutation, errors } = useStockMove((next, key) =>
    api.post("/api/v1/inventory/products/{public_id}/entry/", toEntry(next, key), { public_id: product.id }),
  );
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    mutation.submit(undefined, onClose);
  };
  const costHint = `Vacío: ${formatCop(product.purchase_cost)}, el costo del producto.`;
  return (
    <FormDialog
      title={`Entrada de ${product.name}`}
      subtitle={`Sede ${product.branch ?? ""} · hay ${String(product.stock)}`}
      onClose={onClose}
    >
      <form className={form.form} onSubmit={submit} aria-label="Entrada de stock">
        <StockFields
          draft={draft}
          errors={errors}
          onChange={setDraft}
          quantityLabel="Unidades que entran"
          reasonHint="Por ejemplo: compra a proveedor."
          request="EntryRequest"
        />
        <Field label="Costo unitario" error={errors.fields.unit_cost} hint={costHint}>
          {(control) => (
            <input
              {...control}
              className={cx(input.input, input.figure)}
              inputMode="numeric"
              value={draft.unit_cost}
              onChange={(event) => {
                setDraft({ ...draft, unit_cost: digitsOnly(event.target.value) });
              }}
            />
          )}
        </Field>
        <FormAlert message={errors.detail} />
        <div className={form.actions}>
          <Button kind="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending || draft.quantity === "" || draft.reason.trim() === ""}>
            {mutation.isPending ? "Registrando…" : "Registrar entrada"}
          </Button>
        </div>
      </form>
    </FormDialog>
  );
}
