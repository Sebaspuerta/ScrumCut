import { Boxes, CalendarDays, type LucideIcon } from "lucide-react";
import { Link } from "react-router";

import type { AlertLevel } from "../api/types";
import rowStyles from "../frame/AlertRow.module.css";
import { productPath } from "../lib/appRoutes";
import { shortDate } from "../lib/format";
import { Panel } from "../ui/Panel";
import styles from "./Inventory.module.css";

interface StockAlertListProps {
  title: string;
  items: AlertLevel[];
  count: number;
  kind: "low" | "expiring";
  empty: string;
}

const ICONS: Record<StockAlertListProps["kind"], LucideIcon> = { low: Boxes, expiring: CalendarDays };

function detail(item: AlertLevel, kind: StockAlertListProps["kind"]): string {
  if (kind === "low")
    return `Quedan ${String(item.quantity)} (mínimo ${String(item.minimum_stock ?? 0)}) · ${item.branch}`;
  const when = item.expiration_date ? shortDate(item.expiration_date) : "—";
  return `${item.expired ? "Venció" : "Vence"} el ${when} · ${String(item.quantity)} en ${item.branch}`;
}

/** Un aviso de la sede (stock bajo o por vencer): cada producto enlaza a su panel. */
export function StockAlertList({ title, items, count, kind, empty }: StockAlertListProps) {
  const Icon = ICONS[kind];
  return (
    <Panel title={title} subtitle={count === 1 ? "1 producto" : `${String(count)} productos`}>
      {items.length === 0 ? (
        <p className={styles.muted}>{empty}</p>
      ) : (
        <ul className={styles.lines}>
          {items.map((item) => (
            <li key={`${item.product}-${item.branch}`}>
              <Link className={styles.alertLink} to={productPath(item.product)}>
                <span className={rowStyles.icon} aria-hidden="true">
                  <Icon size={17} />
                </span>
                <span className={rowStyles.text}>
                  <b>{item.name}</b>
                  <small>{detail(item, kind)}</small>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
