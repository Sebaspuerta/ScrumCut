import { Link } from "react-router";

import type { OrderRow } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { clock, formatCop } from "../lib/format";
import { ORDER_PARAM, withParam } from "./orderParams";
import styles from "./OrderList.module.css";

interface OrderRowLinkProps {
  order: OrderRow;
  selected: boolean;
  params: URLSearchParams;
}

function stateText(order: OrderRow, timeZone: string): string {
  if (order.status === "cerrada" && order.closed_at) return `${order.payment} · ${clock(order.closed_at, timeZone)}`;
  if (order.status === "anulada") return `Anulada · ${order.cancel_reason}`;
  return `Abierta desde las ${clock(order.created_at, timeZone)}`;
}

/** Una comanda de la lista: cliente y total; número, barberos y estado; y sus ítems. Abre el panel. */
export function OrderRowLink({ order, selected, params }: OrderRowLinkProps) {
  const timeZone = useTimeZone();
  return (
    <Link
      className={styles.row}
      to={{ search: withParam(params, ORDER_PARAM, order.id).toString() }}
      aria-current={selected ? "true" : undefined}
    >
      <span className={styles.line}>
        <b>{order.client_name}</b>
        <b className={styles.total}>{formatCop(order.total)}</b>
      </span>
      <span className={styles.line}>
        <small>
          #{order.number} · {order.barbers}
        </small>
        <small className={styles.state}>{stateText(order, timeZone)}</small>
      </span>
      <small className={styles.items}>{order.items || "Sin ítems todavía"}</small>
    </Link>
  );
}
