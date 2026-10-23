import type { CalendarDay } from "../api/types";
import { formatCop, longDate } from "../lib/format";
import styles from "./SalesCalendar.module.css";

interface CalendarCellProps {
  day: CalendarDay | null;
}

/** h0 sin ventas, h1 a h5 por nivel; los días futuros, punteados; fuera del mes, vacíos. */
export function cellClass(day: CalendarDay | null): string {
  if (day === null) return styles.outside ?? "";
  if (day.future) return styles.future ?? "";
  return (day.has_sales ? styles[`h${String(day.level + 1)}`] : styles.h0) ?? "";
}

export function CalendarCell({ day }: CalendarCellProps) {
  if (day === null) return <li className={[styles.day, cellClass(day)].join(" ")} aria-hidden="true" />;
  const sold = day.has_sales && !day.future;
  const summary = sold
    ? `${longDate(day.date)}: ${formatCop(day.total)} en ${String(day.orders)} comandas`
    : `${longDate(day.date)}: ${day.future ? "aún no llega" : "sin ventas"}`;
  return (
    <li
      className={[styles.day, cellClass(day), day.today ? styles.today : ""].join(" ")}
      aria-label={summary}
      aria-current={day.today ? "date" : undefined}
      tabIndex={sold ? 0 : undefined}
    >
      <span aria-hidden="true">{day.day}</span>
      {!day.future &&
        (sold ? <b aria-hidden="true">{formatCop(day.total)}</b> : <em aria-hidden="true">Sin ventas</em>)}
      {sold && (
        <span className={styles.tip} aria-hidden="true">
          <strong>{longDate(day.date)}</strong>
          <i>
            Vendido <b>{formatCop(day.total)}</b>
          </i>
          <i>
            Comandas <b>{day.orders}</b>
          </i>
          <i>
            Ticket promedio <b>{formatCop(day.ticket)}</b>
          </i>
        </span>
      )}
    </li>
  );
}
