import { cx } from "../lib/cx";
import styles from "./DashboardSkeleton.module.css";

const METRICS = 5;

/** Cargando: la forma del tablero con bloques que laten (el esqueleto de la referencia). */
export function DashboardSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Cargando el tablero">
      <div className={cx(styles.block, styles.title)} />
      <div className={styles.metrics}>
        {Array.from({ length: METRICS }, (_, index) => (
          <div key={index} className={styles.block} />
        ))}
      </div>
      <div className={styles.panels}>
        <div className={cx(styles.block, styles.panel)} />
        <div className={cx(styles.block, styles.panel)} />
      </div>
    </div>
  );
}
