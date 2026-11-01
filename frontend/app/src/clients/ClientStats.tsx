import type { ClientStats as Stats } from "../api/types";
import { Metric } from "../dashboard/Metric";
import { formatCop } from "../lib/format";
import { Change } from "../ui/Change";
import styles from "./Clients.module.css";

interface ClientStatsProps {
  stats: Stats;
}

function newClientsNote(stats: Stats) {
  const { new_this_month: now, new_last_month: before } = stats;
  const direction = now === before ? null : now > before ? "up" : "down";
  return <Change direction={direction}>{before} el mes anterior</Change>;
}

/** Activos en 90 días, nuevos este mes frente al anterior, vuelven en 30 días y con fiado, en la sede. */
export function ClientStats({ stats }: ClientStatsProps) {
  return (
    <div className={styles.stats} role="list" aria-label="Clientes de la sede">
      <Metric
        label="Activos 90 días"
        value={String(stats.active)}
        note={`de ${String(stats.with_visits)} con visitas`}
      />
      <Metric label="Nuevos este mes" value={String(stats.new_this_month)} note={newClientsNote(stats)} />
      <Metric
        label="Vuelven en 30 días"
        value={stats.return_rate === null ? "—" : `${String(stats.return_rate)} %`}
        note="después de su primera visita"
      />
      <Metric label="Con fiado" value={String(stats.debtors)} note={`${formatCop(stats.debt_total)} por cobrar`} />
    </div>
  );
}
