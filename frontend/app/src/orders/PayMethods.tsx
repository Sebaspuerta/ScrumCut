import { useId } from "react";

import type { CheckoutDraft } from "./checkoutDraft";
import styles from "./PayMethods.module.css";

export interface MethodOption {
  value: string;
  label: string;
}

interface PayMethodsProps {
  draft: CheckoutDraft;
  methods: MethodOption[];
  error: string | undefined;
  onChange: (draft: CheckoutDraft) => void;
}

/** Las formas de pago habilitadas y, con cliente registrado, Fiado: radios nativos con la forma de la referencia. */
export function PayMethods({ draft, methods, error, onChange }: PayMethodsProps) {
  const name = useId();
  return (
    <fieldset className={styles.fieldset} aria-describedby={error ? `${name}-error` : undefined}>
      <legend className="visually-hidden">Forma de pago</legend>
      <div className={styles.grid}>
        {methods.map((method) => (
          <label key={method.value} className={styles.option}>
            <input
              type="radio"
              name={name}
              value={method.value}
              checked={draft.method === method.value}
              onChange={() => {
                onChange({ ...draft, method: method.value });
              }}
            />
            {method.label}
          </label>
        ))}
      </div>
      {error && (
        <p id={`${name}-error`} className={styles.error}>
          {error}
        </p>
      )}
    </fieldset>
  );
}
