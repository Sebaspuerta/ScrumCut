import { Link } from "react-router";

import type { ReceivableRow } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { receivablePath } from "../lib/appRoutes";
import { formatCop, shortDate, zonedDate } from "../lib/format";
import styles from "./Clients.module.css";

interface ClientReceivablesProps {
  receivables: ReceivableRow[];
  branch: string;
}

/** Sus fiados en la sede, los más recientes primero; cada uno abre su detalle y su abono. */
export function ClientReceivables({ receivables, branch }: ClientReceivablesProps) {
  const timeZone = useTimeZone();
  if (receivables.length === 0) return null;
  return (
    <>
      <h3 className={styles.subhead}>Fiados en {branch}</h3>
      <ul className={styles.lines}>
        {receivables.map((receivable) => (
          <li key={receivable.id}>
            <Link className={styles.line} to={receivablePath(receivable.id)}>
              <span>
                {receivable.order ? `Comanda #${String(receivable.order.number)}` : "Fiado manual"}
                <small>
                  {shortDate(zonedDate(receivable.created_at, timeZone))} · {receivable.due_text}
                </small>
              </span>
              <b className={styles.figure}>{formatCop(receivable.balance)}</b>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
