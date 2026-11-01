import { Link } from "react-router";

import type { ClientVisit } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { orderPath } from "../lib/appRoutes";
import { formatCop, shortDate, zonedDate } from "../lib/format";
import styles from "./Clients.module.css";

interface ClientVisitsProps {
  visits: ClientVisit[];
  branch: string;
}

/** Sus últimas visitas en la sede; cada una abre su comanda. */
export function ClientVisits({ visits, branch }: ClientVisitsProps) {
  const timeZone = useTimeZone();
  return (
    <>
      <h3 className={styles.subhead}>Últimas visitas en {branch}</h3>
      {visits.length === 0 ? (
        <p className={styles.muted}>Todavía no tiene visitas en esta sede.</p>
      ) : (
        <ul className={styles.lines}>
          {visits.map((visit) => (
            <li key={visit.id}>
              <Link className={styles.line} to={orderPath(visit.id)}>
                <span>
                  {visit.items || "Sin ítems"}
                  <small>
                    {shortDate(zonedDate(visit.closed_at, timeZone))} · {visit.barber ?? "Sin barbero"} ·{" "}
                    {visit.methods}
                  </small>
                </span>
                <b className={styles.figure}>{formatCop(visit.total)}</b>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
