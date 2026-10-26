import { cx } from "../lib/cx";
import { formatCop } from "../lib/format";
import { fromCents, digitsOnly } from "../lib/money";
import { Field } from "../ui/Field";
import input from "../ui/Input.module.css";
import { changeCents, type CheckoutDraft } from "./checkoutDraft";
import styles from "./OrderDetail.module.css";

interface CashFieldsProps {
  draft: CheckoutDraft;
  total: string;
  error: string | undefined;
  onChange: (draft: CheckoutDraft) => void;
}

function changeText(cents: number | null): string {
  if (cents === null) return "—";
  return cents < 0 ? `Faltan ${formatCop(fromCents(-cents))}` : formatCop(fromCents(cents));
}

/** Lo recibido en efectivo y las vueltas, solo sobre la parte en efectivo (vista previa; las da el servidor). */
export function CashFields({ draft, total, error, onChange }: CashFieldsProps) {
  return (
    <>
      <Field label="Recibido en efectivo" error={error} className={styles.field}>
        {(control) => (
          <input
            {...control}
            className={cx(input.input, input.figure)}
            inputMode="numeric"
            value={draft.received}
            onChange={(event) => {
              onChange({ ...draft, received: digitsOnly(event.target.value) });
            }}
          />
        )}
      </Field>
      <p className={styles.change} aria-live="polite">
        <span>Vueltas</span>
        <b>{changeText(changeCents(draft, total))}</b>
      </p>
    </>
  );
}
