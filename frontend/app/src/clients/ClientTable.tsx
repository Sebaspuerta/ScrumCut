import { Link } from "react-router";

import type { ClientRow } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { CLIENT_PARAM } from "../lib/appRoutes";
import { cx } from "../lib/cx";
import { formatCop, shortDate, zonedDate } from "../lib/format";
import { isZeroAmount } from "../lib/money";
import { withParam } from "../lib/searchParams";
import table from "../ui/Table.module.css";
import styles from "./Clients.module.css";
import { LevelTag } from "./LevelTag";

interface ClientTableProps {
  rows: ClientRow[];
  selected: string | null;
  params: URLSearchParams;
  branch: string;
}

const EMPTY = "—";

function Row({ row, selected, params }: { row: ClientRow; selected: boolean; params: URLSearchParams }) {
  const timeZone = useTimeZone();
  const lastVisit = row.last_visit ? shortDate(zonedDate(row.last_visit, timeZone)) : EMPTY;
  return (
    <tr className={cx(selected && styles.current)}>
      <td>
        <Link
          className={styles.rowLink}
          to={{ search: withParam(params, CLIENT_PARAM, row.id).toString() }}
          aria-current={selected ? "true" : undefined}
        >
          <b>{row.name}</b>
          <small>{row.phone ?? "Sin celular"}</small>
        </Link>
      </td>
      <td>
        <LevelTag level={row.level} label={row.level_label} />
      </td>
      <td className={cx(table.num, styles.wide)}>{row.visits ?? EMPTY}</td>
      <td className={styles.wide}>{lastVisit}</td>
      <td className={cx(table.num, styles.wide)}>{row.spent_recent === null ? EMPTY : formatCop(row.spent_recent)}</td>
      <td className={table.num}>
        {row.debt === null || isZeroAmount(row.debt) ? EMPTY : <b>{formatCop(row.debt)}</b>}
      </td>
    </tr>
  );
}

/** Cliente (con el celular enmascarado), nivel, visitas, última visita, gasto de 90 días y deuda en la sede. */
export function ClientTable({ rows, selected, params, branch }: ClientTableProps) {
  if (rows.length === 0) {
    return <p className={styles.empty}>Ningún cliente coincide. Revisa la búsqueda o crea uno nuevo.</p>;
  }
  return (
    <table className={table.table}>
      <caption className="visually-hidden">Clientes de la sede {branch}</caption>
      <thead>
        <tr>
          <th scope="col">Cliente</th>
          <th scope="col">Nivel</th>
          <th scope="col" className={cx(table.num, styles.wide)}>
            Visitas
          </th>
          <th scope="col" className={styles.wide}>
            Última visita
          </th>
          <th scope="col" className={cx(table.num, styles.wide)}>
            Gasto 90 días
          </th>
          <th scope="col" className={table.num}>
            Debe
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <Row key={row.id} row={row} selected={row.id === selected} params={params} />
        ))}
      </tbody>
    </table>
  );
}
