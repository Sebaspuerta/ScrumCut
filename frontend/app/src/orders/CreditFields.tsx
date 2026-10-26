import type { OrderDetail } from "../api/types";
import { formatCop } from "../lib/format";
import { Field } from "../ui/Field";
import input from "../ui/Input.module.css";
import type { CheckoutDraft } from "./checkoutDraft";
import styles from "./OrderDetail.module.css";

interface CreditFieldsProps {
  draft: CheckoutDraft;
  credit: NonNullable<OrderDetail["credit"]>;
  branch: string;
  error: string | undefined;
  onChange: (draft: CheckoutDraft) => void;
}

/** El fiado: lo que el cliente debe en la sede, su cupo y la fecha acordada de pago. */
export function CreditFields({ draft, credit, branch, error, onChange }: CreditFieldsProps) {
  return (
    <>
      <dl className={styles.totals}>
        {credit.available !== null && (
          <div className={styles.totalRow}>
            <dt>Cupo disponible en {branch}</dt>
            <dd>{formatCop(credit.available)}</dd>
          </div>
        )}
        <div className={styles.totalRow}>
          <dt>Debe hoy en {branch}</dt>
          <dd>{formatCop(credit.debt)}</dd>
        </div>
      </dl>
      <p className={styles.muted}>El fiado se paga solo en la sede {branch}.</p>
      <Field label="Fecha acordada de pago" error={error} className={styles.field}>
        {(control) => (
          <input
            {...control}
            className={input.input}
            type="date"
            value={draft.dueDate}
            onChange={(event) => {
              onChange({ ...draft, dueDate: event.target.value });
            }}
          />
        )}
      </Field>
    </>
  );
}
