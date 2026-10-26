import type { ReactNode } from "react";

import styles from "./Metric.module.css";
import { Sparkline } from "./Sparkline";

interface MetricProps {
  label: string;
  value: string;
  note: ReactNode;
  /** Los últimos días del período; sin serie, no hay mini tendencia. */
  trend?: number[];
}

export function Metric({ label, value, note, trend }: MetricProps) {
  return (
    <div className={styles.metric} role="listitem">
      <span className={styles.label}>{label}</span>
      <strong className={styles.value}>{value}</strong>
      {trend && trend.length > 1 && <Sparkline values={trend} />}
      <small className={styles.delta}>{note}</small>
    </div>
  );
}
