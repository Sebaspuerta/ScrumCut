import { cx } from "../lib/cx";
import { asTyped, digitsOnly } from "../lib/money";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import input from "../ui/Input.module.css";
import type { PaymentDraft } from "./paymentDraft";
import styles from "./Receivables.module.css";

interface AmountFieldProps {
  draft: PaymentDraft;
  balance: string;
  error: string | undefined;
  onChange: (draft: PaymentDraft) => void;
}

/** El monto del abono en pesos, sin puntos ni decimales, y «Pagar todo» con el saldo que muestra el servidor. */
export function AmountField({ draft, balance, error, onChange }: AmountFieldProps) {
  return (
    <Field label="Monto del abono" error={error}>
      {(control) => (
        <div className={styles.amountRow}>
          <input
            {...control}
            className={cx(input.input, input.figure)}
            inputMode="numeric"
            value={draft.amount}
            onChange={(event) => {
              onChange({ ...draft, amount: digitsOnly(event.target.value) });
            }}
          />
          <Button
            kind="secondary"
            onClick={() => {
              onChange({ ...draft, amount: asTyped(balance) });
            }}
          >
            Pagar todo
          </Button>
        </div>
      )}
    </Field>
  );
}
