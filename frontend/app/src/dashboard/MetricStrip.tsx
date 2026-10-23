import type { Dashboard } from "../api/types";
import { clock, formatCop, formatVariation } from "../lib/format";
import { Metric } from "./Metric";
import styles from "./MetricStrip.module.css";

interface MetricStripProps {
  data: Dashboard;
}

type Variation = Dashboard["kpis"]["income"]["variation"];

function compared(variation: Variation, against: string): string {
  return variation ? `${formatVariation(variation.percent)} ${against}` : "Sin datos para comparar";
}

function cashNote(data: Dashboard): string {
  const cash = data.kpis.cash;
  return cash ? `${data.scope_label} · desde las ${clock(cash.opened_at, data.timezone)}` : "Sin caja abierta";
}

/** Los cinco indicadores de la referencia, con las cifras del servidor ya calculadas. */
export function MetricStrip({ data }: MetricStripProps) {
  const { kpis, trend } = data;
  const receivables = kpis.receivables;
  const trendOf = (values: readonly (string | number)[]) => values.map(Number);
  return (
    <div className={styles.metrics} role="list" aria-label="Indicadores">
      <Metric
        label="Ingresos de hoy"
        value={formatCop(kpis.income.value)}
        note={compared(kpis.income.variation, kpis.comparison)}
        trend={trendOf(trend.income)}
      />
      <Metric
        label="Comandas cerradas"
        value={String(kpis.orders.value)}
        note={kpis.orders.open === 1 ? "1 abierta ahora" : `${String(kpis.orders.open)} abiertas ahora`}
        trend={trendOf(trend.orders)}
      />
      <Metric
        label="Ticket promedio"
        value={formatCop(kpis.ticket.value)}
        note={compared(kpis.ticket.variation, "vs. período anterior")}
        trend={trendOf(trend.ticket)}
      />
      <Metric label="Esperado en caja" value={kpis.cash ? formatCop(kpis.cash.expected) : "—"} note={cashNote(data)} />
      <Metric
        label="Fiados pendientes"
        value={formatCop(receivables.pending_balance)}
        note={`${String(receivables.overdue_count)} vencidos · ${String(receivables.clients)} clientes`}
      />
    </div>
  );
}
