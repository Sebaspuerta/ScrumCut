import type { FormErrors } from "../api/errors";
import type { CashState } from "../api/types";
import { cx } from "../lib/cx";
import { MAX_LENGTH } from "../lib/fieldLimits";
import { formatCop } from "../lib/format";
import { digitsOnly } from "../lib/money";
import { Field } from "../ui/Field";
import input from "../ui/Input.module.css";
import styles from "./Cash.module.css";
import { billSubtotal, type CountDraft } from "./countDraft";

interface CountInputsProps {
  state: CashState;
  draft: CountDraft;
  errors: FormErrors["fields"];
  hasDifference: boolean;
  onChange: (draft: CountDraft) => void;
}

/** Una fila por billete (cuántos hay y su subtotal), las monedas en total y la nota de la diferencia. */
export function CountInputs({ state, draft, errors, hasDifference, onChange }: CountInputsProps) {
  return (
    <div className={styles.countInputs}>
      {state.denominations.map((denomination) => {
        const count = draft.bills[denomination] ?? "";
        return (
          <div key={denomination} className={styles.denom}>
            <label htmlFor={`billetes-${String(denomination)}`}>{formatCop(String(denomination))}</label>
            <input
              id={`billetes-${String(denomination)}`}
              className={cx(input.input, input.figure)}
              inputMode="numeric"
              value={count}
              onChange={(event) => {
                onChange({ ...draft, bills: { ...draft.bills, [denomination]: digitsOnly(event.target.value) } });
              }}
            />
            <b>{formatCop(billSubtotal(draft, denomination))}</b>
          </div>
        );
      })}
      {errors.bills && <p className={styles.error}>{errors.bills}</p>}
      <Field label="Monedas (total en pesos)" error={errors.coins}>
        {(control) => (
          <input
            {...control}
            className={cx(input.input, input.figure)}
            inputMode="numeric"
            value={draft.coins}
            onChange={(event) => {
              onChange({ ...draft, coins: digitsOnly(event.target.value) });
            }}
          />
        )}
      </Field>
      <Field
        label={hasDifference ? "Explica la diferencia (obligatorio)" : "Nota del cierre"}
        error={errors.notes}
        hint={hasDifference ? "Hay diferencia entre el contado y el esperado." : undefined}
      >
        {(control) => (
          <textarea
            {...control}
            className={input.input}
            rows={2}
            maxLength={MAX_LENGTH.CloseCashRequest.notes}
            placeholder="Ej.: vueltas mal entregadas en la comanda #0131"
            value={draft.notes}
            onChange={(event) => {
              onChange({ ...draft, notes: event.target.value });
            }}
          />
        )}
      </Field>
    </div>
  );
}
