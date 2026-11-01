import type { ReceivableDetail } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { clock, formatCop, shortDate, zonedDate } from "../lib/format";
import styles from "./Receivables.module.css";

interface PaymentHistoryProps {
  payments: ReceivableDetail["payments"];
}

/** Los abonos anteriores, el más reciente primero, con su forma de pago, su referencia y quién lo recibió. */
export function PaymentHistory({ payments }: PaymentHistoryProps) {
  const timeZone = useTimeZone();
  return (
    <>
      <h3 className={styles.subhead}>Abonos anteriores</h3>
      {payments.length === 0 ? (
        <p className={styles.muted}>Todavía no ha abonado.</p>
      ) : (
        <ul className={styles.lines} aria-label="Abonos anteriores">
          {payments.map((payment) => (
            <li key={payment.id} className={styles.line}>
              <span>
                {shortDate(zonedDate(payment.at, timeZone))} · {clock(payment.at, timeZone)}
                <small>
                  {payment.method}
                  {payment.reference && ` · Ref. ${payment.reference}`} · recibió {payment.received_by}
                </small>
              </span>
              <b className={styles.figure}>{formatCop(payment.amount)}</b>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
