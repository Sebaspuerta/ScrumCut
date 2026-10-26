import type { CashSession } from "../api/types";
import { Metric } from "../dashboard/Metric";
import { useTimeZone } from "../hooks/useMe";
import { clock, countOf, formatCop, outflowCop, signedCop } from "../lib/format";
import styles from "./Cash.module.css";

interface CashStripProps {
  session: CashSession;
}

/** Base, ventas en efectivo, abonos, gastos, retiros y esperado: lo que entra y sale de la caja física. */
export function CashStrip({ session }: CashStripProps) {
  const timeZone = useTimeZone();
  const { sales, receivable_payments: payments, expenses, withdrawals } = session.strip;
  return (
    <div className={styles.strip} role="list" aria-label="Resumen de la caja">
      <Metric
        label="Base de apertura"
        value={formatCop(session.opening_amount)}
        note={clock(session.opened_at, timeZone)}
      />
      <Metric
        label="Ventas en efectivo"
        value={signedCop(sales.total)}
        note={countOf(sales.count, "comanda", "comandas")}
      />
      <Metric
        label="Abonos de fiados"
        value={signedCop(payments.total)}
        note={countOf(payments.count, "abono", "abonos")}
      />
      <Metric label="Gastos" value={outflowCop(expenses.total)} note={countOf(expenses.count, "gasto", "gastos")} />
      <Metric
        label="Retiros"
        value={outflowCop(withdrawals.total)}
        note={countOf(withdrawals.count, "retiro", "retiros")}
      />
      <Metric label="Esperado en caja" value={formatCop(session.expected)} note="Lo que debe haber" />
    </div>
  );
}
