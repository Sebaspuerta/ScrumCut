import { Link } from "react-router";

import type { ReceivableRow } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { RECEIVABLE_PARAM } from "../lib/appRoutes";
import { cx } from "../lib/cx";
import { formatCop, shortDate, zonedDate } from "../lib/format";
import { isZeroAmount } from "../lib/money";
import { withParam } from "../lib/searchParams";
import table from "../ui/Table.module.css";
import { DueText } from "./DueText";
import styles from "./Receivables.module.css";

interface ReceivableTableProps {
  rows: ReceivableRow[];
  selected: string | null;
  params: URLSearchParams;
  branch: string;
}

const origin = (row: ReceivableRow) =>
  `${row.order ? `Comanda #${String(row.order.number)}` : "Fiado manual"} · ${row.branch}`;

function Row({ row, selected, params }: { row: ReceivableRow; selected: boolean; params: URLSearchParams }) {
  const timeZone = useTimeZone();
  return (
    <tr className={cx(selected && styles.current)}>
      <td>
        <Link
          className={styles.rowLink}
          to={{ search: withParam(params, RECEIVABLE_PARAM, row.id).toString() }}
          aria-current={selected ? "true" : undefined}
        >
          <b>{row.client.name}</b>
          <small>{origin(row)}</small>
        </Link>
      </td>
      <td className={styles.wide}>{shortDate(zonedDate(row.created_at, timeZone))}</td>
      <td className={styles.wide}>{row.due_date ? shortDate(row.due_date) : "—"}</td>
      <td className={cx(table.num, styles.wide)}>{formatCop(row.total)}</td>
      <td className={cx(table.num, styles.wide)}>{isZeroAmount(row.paid) ? "—" : formatCop(row.paid)}</td>
      <td className={table.num}>
        <b>{formatCop(row.balance)}</b>
      </td>
      <td>
        <DueText receivable={row} />
      </td>
    </tr>
  );
}

/** Cliente y origen, fecha, vencimiento, total, abonado, saldo y estado; los vivos por urgencia. */
export function ReceivableTable({ rows, selected, params, branch }: ReceivableTableProps) {
  if (rows.length === 0) return <p className={styles.empty}>No hay fiados en esta pestaña.</p>;
  return (
    <div className={styles.tableScroll}>
      <table className={table.table}>
        <caption className="visually-hidden">Fiados de la sede {branch}, los vencidos primero</caption>
        <thead>
          <tr>
            <th scope="col">Cliente</th>
            <th scope="col" className={styles.wide}>
              Fiado el
            </th>
            <th scope="col" className={styles.wide}>
              Vence
            </th>
            <th scope="col" className={cx(table.num, styles.wide)}>
              Total
            </th>
            <th scope="col" className={cx(table.num, styles.wide)}>
              Abonado
            </th>
            <th scope="col" className={table.num}>
              Saldo
            </th>
            <th scope="col">Estado</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <Row key={row.id} row={row} selected={row.id === selected} params={params} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
