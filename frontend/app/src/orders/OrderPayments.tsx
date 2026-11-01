import { Link } from "react-router";

import type { OrderDetail } from "../api/types";
import { receivablePath } from "../lib/appRoutes";
import { formatCop } from "../lib/format";
import { isZeroAmount } from "../lib/money";
import styles from "./OrderDetail.module.css";

interface OrderPaymentsProps {
  order: OrderDetail;
}

/** Cómo se cobró una comanda cerrada y, si quedó saldo, lo que quedó como fiado, con el enlace a ese fiado. */
export function OrderPayments({ order }: OrderPaymentsProps) {
  const credit = !isZeroAmount(order.balance);
  const receivable = order.receivable;
  return (
    <div className={styles.section}>
      <h3 className={styles.subhead}>Cobro</h3>
      <ul className={styles.lines} aria-label="Pagos">
        {order.payments.map((payment, index) => (
          <li key={`${payment.method}-${String(index)}`} className={styles.line}>
            <span className={styles.lineText}>
              <b>{payment.method}</b>
              {payment.reference && <small>Ref. {payment.reference}</small>}
            </span>
            <b className={styles.figure}>{formatCop(payment.amount)}</b>
          </li>
        ))}
        {credit && (
          <li className={styles.line}>
            <span className={styles.lineText}>
              <b>Fiado</b>
              {receivable && <Link to={receivablePath(receivable.id)}>Ver el fiado y sus abonos</Link>}
            </span>
            <b className={styles.figure}>{formatCop(order.balance)}</b>
          </li>
        )}
      </ul>
    </div>
  );
}
