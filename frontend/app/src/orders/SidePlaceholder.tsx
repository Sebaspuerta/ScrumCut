import type { OrderList } from "../api/types";
import { formatCop } from "../lib/format";
import styles from "./OrderDetail.module.css";

interface SidePlaceholderProps {
  list: OrderList | undefined;
}

/** Sin comanda elegida: en las cerradas, lo cobrado del día por medio; en las demás, cómo empezar. */
export function SidePlaceholder({ list }: SidePlaceholderProps) {
  const summary = list?.summary;
  const cells = summary
    ? [
        { label: "Efectivo", amount: summary.cash },
        { label: "Otros medios", amount: summary.other },
        { label: "Fiado", amount: summary.credit },
      ]
    : [];
  return (
    <section className={styles.panel} aria-label="Detalle de la comanda">
      {summary && (
        <dl className={styles.summary} aria-label="Cobrado en el día">
          {cells.map((cell) => (
            <div key={cell.label}>
              <dt>{cell.label}</dt>
              <dd>{formatCop(cell.amount)}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className={styles.muted}>Elige una comanda de la lista para ver su detalle y cobrarla.</p>
    </section>
  );
}
