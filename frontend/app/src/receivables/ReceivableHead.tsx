import { X } from "lucide-react";
import { Link } from "react-router";

import type { ReceivableDetail } from "../api/types";
import { clientPath, orderPath } from "../lib/appRoutes";
import { shortDate } from "../lib/format";
import { DueText } from "./DueText";
import styles from "./Receivables.module.css";

interface ReceivableHeadProps {
  receivable: ReceivableDetail;
  titleId: string;
  onClose: () => void;
}

function dueDate(receivable: ReceivableDetail): string {
  if (!receivable.due_date || receivable.due_tone === "done") return "";
  const verb = receivable.due_tone === "overdue" ? "venció" : "vence";
  return ` · ${verb} el ${shortDate(receivable.due_date)}`;
}

/** El origen (comanda o fiado manual) y su sede, el cliente con enlace a su ficha y el estado, sin rojos. */
export function ReceivableHead({ receivable, titleId, onClose }: ReceivableHeadProps) {
  const order = receivable.order;
  return (
    <div className={styles.head}>
      <div>
        <p className={styles.eyebrow}>
          {order ? `Comanda #${String(order.number)}` : "Fiado manual"} · {receivable.branch}
        </p>
        <h2 id={titleId}>
          <Link className={styles.client} to={clientPath(receivable.client.id)}>
            {receivable.client.name}
          </Link>
        </h2>
        <p>
          <DueText receivable={receivable} />
          <span className={styles.muted}>{dueDate(receivable)}</span>
        </p>
        {order && <Link to={orderPath(order.id)}>Ver la comanda #{order.number}</Link>}
      </div>
      <button type="button" className={styles.close} aria-label="Cerrar el detalle" onClick={onClose}>
        <X size={18} aria-hidden="true" />
      </button>
    </div>
  );
}
