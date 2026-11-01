import type { Aging } from "../api/types";
import { cssVar } from "../lib/cssVar";
import { cx } from "../lib/cx";
import { formatCop } from "../lib/format";
import styles from "./Receivables.module.css";

interface AgingStripProps {
  aging: Aging[];
  total: string;
}

/** La antigüedad de la deuda: el total por cobrar y cuatro tramos, del más nuevo al más viejo, con su parte. */
export function AgingStrip({ aging, total }: AgingStripProps) {
  return (
    <dl className={styles.aging} aria-label="Antigüedad de la deuda">
      <div className={styles.total}>
        <dt>Cartera total</dt>
        <dd>{formatCop(total)}</dd>
      </div>
      {aging.map((bucket) => (
        <div key={bucket.key}>
          <dt>{bucket.label}</dt>
          <dd>
            <b>{bucket.percent} %</b>
          </dd>
          <dd className={cx(styles.muted, styles.wideCell)}>{formatCop(bucket.amount)}</dd>
          <dd className={styles.bar} aria-hidden="true">
            <i ref={cssVar("--share", `${String(bucket.percent)}%`)} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
