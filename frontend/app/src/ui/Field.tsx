import { useId, type ReactNode } from "react";

import styles from "./Field.module.css";

export interface ControlProps {
  id: string;
  "aria-invalid": boolean;
  "aria-describedby": string | undefined;
}

interface FieldProps {
  label: string;
  error?: string | undefined;
  hint?: string | undefined;
  /** El control recibe su id y la relación con el error, para que el lector de pantalla lo anuncie. */
  children: (control: ControlProps) => ReactNode;
  className?: string | undefined;
}

/** Un campo con su etiqueta, su ayuda y su error asociado. */
export function Field({ label, error, hint, children, className }: FieldProps) {
  const id = useId();
  const described = [error ? `${id}-error` : "", hint ? `${id}-hint` : ""].filter(Boolean).join(" ");
  return (
    <div className={[styles.field, className ?? ""].join(" ")}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      {children({ id, "aria-invalid": Boolean(error), "aria-describedby": described || undefined })}
      {hint && (
        <p id={`${id}-hint`} className={styles.hint}>
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className={styles.error}>
          {error}
        </p>
      )}
    </div>
  );
}
