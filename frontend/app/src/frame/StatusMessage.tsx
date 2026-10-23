import type { ReactNode } from "react";

import styles from "./StatusMessage.module.css";

interface StatusMessageProps {
  kind: "loading" | "error" | "empty";
  children: ReactNode;
  onRetry?: () => void;
}

/** Estados cargando, error y vacío. El error se anuncia de inmediato; los otros, sin interrumpir. */
export function StatusMessage({ kind, children, onRetry }: StatusMessageProps) {
  return (
    <div className={styles.status} role={kind === "error" ? "alert" : "status"} aria-busy={kind === "loading"}>
      <p>{children}</p>
      {onRetry && (
        <button type="button" className={styles.retry} onClick={onRetry}>
          Reintentar
        </button>
      )}
    </div>
  );
}
