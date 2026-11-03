import type { Production } from "../api/types";
import { Metric } from "../dashboard/Metric";
import { countOf, formatCop } from "../lib/format";
import styles from "./MyCuts.module.css";

interface MyCutsSummaryProps {
  label: string;
  period: Production;
}

/** Cortes, venta y comisión del barbero en un período, tal como los entrega el servidor. */
export function MyCutsSummary({ label, period }: MyCutsSummaryProps) {
  return (
    <div className={styles.stats} role="list" aria-label={label}>
      <Metric
        label={`Cortes · ${label}`}
        value={String(period.cuts)}
        note={countOf(period.orders, "comanda", "comandas")}
      />
      <Metric label={`Producción · ${label}`} value={formatCop(period.production)} note="Lo que vendiste" />
      <Metric label={`Tu comisión · ${label}`} value={formatCop(period.commission)} />
    </div>
  );
}
