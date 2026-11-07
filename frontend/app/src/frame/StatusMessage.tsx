import type { ReactNode } from "react";
import { Link } from "react-router";

import styles from "./StatusMessage.module.css";

interface StatusMessageProps {
  kind: "loading" | "error" | "empty";
  children: ReactNode;
  onRetry?: (() => void) | undefined;
  /** "Volver al inicio": para salir de una pantalla que falló. */
  homeLink?: boolean;
}

/** Estados cargando, error y vacío. El error se anuncia de inmediato; los otros, sin interrumpir. */
export function StatusMessage({ kind, children, onRetry, homeLink = false }: StatusMessageProps) {
  return (
    <div className={styles.status} role={kind === "error" ? "alert" : "status"} aria-busy={kind === "loading"}>
      <p>{children}</p>
      {onRetry && (
        <button type="button" className={styles.retry} onClick={onRetry}>
          Reintentar
        </button>
      )}
      {homeLink && (
        <Link to="/" className={styles.retry}>
          Volver al inicio
        </Link>
      )}
    </div>
  );
}
