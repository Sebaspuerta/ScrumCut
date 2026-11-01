import type { Portfolio } from "../api/types";
import { Metric } from "../dashboard/Metric";
import { countOf, formatCop, monthName } from "../lib/format";
import styles from "./Receivables.module.css";

interface PortfolioStripProps {
  portfolio: Portfolio;
  today: string;
}

const clients = (count: number) => countOf(count, "cliente", "clientes");

/** Por cobrar, vencido, vence en 7 días y cobrado en el mes, en las sedes del alcance. */
export function PortfolioStrip({ portfolio, today }: PortfolioStripProps) {
  const { pending, overdue, due_soon: soon, collected } = portfolio;
  const share = overdue.share === null ? "" : ` · ${String(overdue.share)} % de la cartera`;
  return (
    <div className={styles.strip} role="list" aria-label="Cartera de la sede">
      <Metric
        label="Por cobrar"
        value={formatCop(pending.total)}
        note={`${countOf(pending.count, "fiado", "fiados")} de ${clients(pending.clients)}`}
      />
      <Metric label="Vencido" value={formatCop(overdue.total)} note={`${clients(overdue.clients)}${share}`} />
      <Metric label="Vence en 7 días" value={formatCop(soon.total)} note={clients(soon.clients)} />
      <Metric
        label={`Cobrado en ${monthName(today)}`}
        value={formatCop(collected.total)}
        note={countOf(collected.count, "abono", "abonos")}
      />
    </div>
  );
}
