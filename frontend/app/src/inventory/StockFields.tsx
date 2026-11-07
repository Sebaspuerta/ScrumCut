import type { FormErrors } from "../api/errors";
import { cx } from "../lib/cx";
import { MAX_LENGTH, MAX_VALUE } from "../lib/fieldLimits";
import { digitsOnly } from "../lib/money";
import { Field } from "../ui/Field";
import input from "../ui/Input.module.css";
import type { StockDraft } from "./stockDraft";

interface StockFieldsProps {
  draft: StockDraft;
  errors: FormErrors;
  onChange: (draft: StockDraft) => void;
  quantityLabel: string;
  reasonHint: string;
  /** La petición de este movimiento: de su esquema salen los topes de la cantidad y del motivo. */
  request: "EntryRequest" | "AdjustmentRequest" | "TransferRequest";
}

/** La cantidad (entera, con el teclado numérico del celular y el tope del esquema) y el motivo, obligatorio en todo movimiento. */
export function StockFields({ draft, errors, onChange, quantityLabel, reasonHint, request }: StockFieldsProps) {
  return (
    <>
      <Field label={quantityLabel} error={errors.fields.quantity}>
        {(control) => (
          <input
            {...control}
            data-autofocus
            className={cx(input.input, input.figure)}
            type="number"
            inputMode="numeric"
            min={1}
            max={MAX_VALUE[request].quantity}
            step={1}
            required
            value={draft.quantity}
            onChange={(event) => {
              onChange({ ...draft, quantity: digitsOnly(event.target.value) });
            }}
          />
        )}
      </Field>
      <Field label="Motivo" error={errors.fields.reason} hint={reasonHint}>
        {(control) => (
          <input
            {...control}
            className={input.input}
            required
            maxLength={MAX_LENGTH[request].reason}
            value={draft.reason}
            onChange={(event) => {
              onChange({ ...draft, reason: event.target.value });
            }}
          />
        )}
      </Field>
    </>
  );
}
