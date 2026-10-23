import { Boxes, CalendarDays, CreditCard, Package, type LucideIcon } from "lucide-react";

import type { AlertItem } from "../api/types";
import { clock, shortDate, zonedDate } from "../lib/format";
import styles from "./AlertRow.module.css";

const KIND_ICONS: Record<AlertItem["kind"], LucideIcon> = {
  agotado: Package,
  stock_bajo: Boxes,
  por_vencer: CalendarDays,
  fiado_vencido: CreditCard,
};

interface AlertRowProps {
  alert: AlertItem;
  timeZone: string;
}

function when(createdAt: string, timeZone: string): string {
  const day = zonedDate(createdAt, timeZone);
  const today = zonedDate(new Date().toISOString(), timeZone);
  return day === today ? clock(createdAt, timeZone) : shortDate(day);
}

/** Una alerta: su tipo con ícono, el mensaje, la sede y cuándo; el punto marca las no leídas. */
export function AlertRow({ alert, timeZone }: AlertRowProps) {
  const Icon = KIND_ICONS[alert.kind];
  return (
    <div className={styles.row}>
      <span className={styles.icon} aria-hidden="true">
        <Icon size={17} />
      </span>
      <span className={styles.text}>
        <b>{alert.message}</b>
        <small>
          {alert.kind_label} · {alert.branch} · {when(alert.created_at, timeZone)}
        </small>
      </span>
      {alert.unread && (
        <i className={styles.dot}>
          <span className="visually-hidden">Sin leer</span>
        </i>
      )}
    </div>
  );
}
