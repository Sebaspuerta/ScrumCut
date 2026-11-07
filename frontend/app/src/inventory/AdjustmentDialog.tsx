import type { SubmitEvent } from "react";

import { api } from "../api/client";
import type { ProductDetail } from "../api/types";
import { Button } from "../ui/Button";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";
import styles from "./Inventory.module.css";
import { StockFields } from "./StockFields";
import { toAdjustment, type StockDraft } from "./stockDraft";
import { useStockMove } from "./useStockMove";

interface AdjustmentDialogProps {
  product: ProductDetail;
  onClose: () => void;
}

const DIRECTIONS: { value: StockDraft["direction"]; label: string }[] = [
  { value: "restar", label: "Restar (merma, daño o conteo)" },
  { value: "sumar", label: "Sumar (conteo)" },
];

/** Regla 34: corrige la existencia de la sede con signo y motivo obligatorio; el servidor no la deja negativa. */
export function AdjustmentDialog({ product, onClose }: AdjustmentDialogProps) {
  const { draft, setDraft, mutation, errors } = useStockMove((next, key) =>
    api.post("/api/v1/inventory/products/{public_id}/adjustment/", toAdjustment(next, key), { public_id: product.id }),
  );
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    mutation.submit(undefined, onClose);
  };
  return (
    <FormDialog
      title={`Ajuste de ${product.name}`}
      subtitle={`Sede ${product.branch ?? ""} · hay ${String(product.stock)}`}
      onClose={onClose}
    >
      <form className={form.form} onSubmit={submit} aria-label="Ajuste de stock">
        <fieldset className={styles.choices}>
          <legend className="visually-hidden">Sentido del ajuste</legend>
          {DIRECTIONS.map((direction) => (
            <label key={direction.value} className={styles.choice}>
              <input
                type="radio"
                name="direction"
                checked={draft.direction === direction.value}
                onChange={() => {
                  setDraft({ ...draft, direction: direction.value });
                }}
              />
              {direction.label}
            </label>
          ))}
        </fieldset>
        <StockFields
          draft={draft}
          errors={errors}
          onChange={setDraft}
          quantityLabel="Unidades"
          reasonHint="Obligatorio: queda en el historial."
          request="AdjustmentRequest"
        />
        <FormAlert message={errors.detail} />
        <div className={form.actions}>
          <Button kind="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending || draft.quantity === "" || draft.reason.trim() === ""}>
            {mutation.isPending ? "Registrando…" : "Registrar ajuste"}
          </Button>
        </div>
      </form>
    </FormDialog>
  );
}
