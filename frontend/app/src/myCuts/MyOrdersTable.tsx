import type { MyOrder } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { clock, formatCop } from "../lib/format";
import table from "../ui/Table.module.css";
import styles from "./MyCuts.module.css";

interface MyOrdersTableProps {
  rows: MyOrder[];
}

function Row({ row }: { row: MyOrder }) {
  const timeZone = useTimeZone();
  return (
    <tr>
      <td>
        <span className={styles.order}>
          <b>
            #{row.number} · {clock(row.closed_at, timeZone)}
          </b>
          <small>{row.items}</small>
        </span>
      </td>
      <td className={table.num}>{formatCop(row.production)}</td>
      <td className={table.num}>{formatCop(row.commission)}</td>
    </tr>
  );
}

/** Solo lo del barbero en cada comanda: sus líneas, su producción y su comisión. */
export function MyOrdersTable({ rows }: MyOrdersTableProps) {
  if (rows.length === 0) return <p className={table.empty}>No tienes cortes registrados este día.</p>;
  return (
    <table className={table.table}>
      <caption className="visually-hidden">Tus comandas cerradas del día</caption>
      <thead>
        <tr>
          <th scope="col">Comanda</th>
          <th scope="col" className={table.num}>
            Producción
          </th>
          <th scope="col" className={table.num}>
            Comisión
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <Row key={row.id} row={row} />
        ))}
      </tbody>
    </table>
  );
}
