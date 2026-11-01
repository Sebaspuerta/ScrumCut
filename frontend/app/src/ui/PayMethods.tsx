import { useId } from "react";

import styles from "./PayMethods.module.css";

export interface MethodOption {
  value: string;
  label: string;
}

interface PayMethodsProps {
  value: string;
  methods: MethodOption[];
  error: string | undefined;
  onChange: (method: string) => void;
}

/** Las formas de pago que ofrece el servidor (en el cobro, también Fiado): radios nativos con la forma de la
 * referencia. */
export function PayMethods({ value, methods, error, onChange }: PayMethodsProps) {
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
              checked={value === method.value}
              onChange={() => {
                onChange(method.value);
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
