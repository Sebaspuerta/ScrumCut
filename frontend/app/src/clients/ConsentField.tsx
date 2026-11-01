import type { DataPolicy } from "../api/types";
import form from "../ui/Form.module.css";
import styles from "./Clients.module.css";

interface ConsentFieldProps {
  policy: DataPolicy;
  checked: boolean;
  error: string | undefined;
  onChange: (checked: boolean) => void;
}

/** La autorización de tratamiento de datos (Ley 1581): sin ella el servidor no registra al cliente. Queda guardada
 * con la versión vigente de la política. */
export function ConsentField({ policy, checked, error, onChange }: ConsentFieldProps) {
  return (
    <div>
      <label className={form.check}>
        <input
          type="checkbox"
          checked={checked}
          aria-invalid={Boolean(error)}
          onChange={(event) => {
            onChange(event.target.checked);
          }}
        />
        El cliente autoriza el tratamiento de sus datos personales
      </label>
      <p className={styles.muted}>
        Según la{" "}
        <a href={policy.url} target="_blank" rel="noopener noreferrer">
          política de tratamiento de datos
        </a>{" "}
        vigente (versión {policy.version}).
      </p>
      {error && (
        <p className={styles.fieldError} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
