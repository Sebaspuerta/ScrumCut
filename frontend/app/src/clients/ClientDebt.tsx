import { Link } from "react-router";

import type { ClientActivity } from "../api/types";
import { receivablePath } from "../lib/appRoutes";
import { formatCop } from "../lib/format";
import { isZeroAmount } from "../lib/money";
import styles from "./Clients.module.css";

interface ClientDebtProps {
  activity: ClientActivity;
  branch: string;
}

/** Lo que debe en la sede, con el enlace a su fiado más antiguo para abonarlo. */
export function ClientDebt({ activity, branch }: ClientDebtProps) {
  if (isZeroAmount(activity.balance)) {
    return <p className={styles.debt}>No debe nada en {branch}</p>;
  }
  return (
    <div className={styles.debt}>
      <span>
        <b>Debe {formatCop(activity.balance)}</b> en {branch}
      </span>
      {activity.open_debt && <Link to={receivablePath(activity.open_debt)}>Ver fiado y abonar</Link>}
    </div>
  );
}
