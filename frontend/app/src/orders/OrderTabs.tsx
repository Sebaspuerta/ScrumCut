import { Link } from "react-router";

import type { OrderList, OrderTab } from "../api/types";
import { ORDER_PARAM, withFilter } from "./orderParams";
import styles from "./OrderTabs.module.css";

interface OrderTabsProps {
  tabs: OrderList["tabs"];
  current: OrderTab;
  params: URLSearchParams;
}

/** Abiertas, Cerradas y Anuladas con su conteo: enlaces con aria-current, el estado va en la URL. */
export function OrderTabs({ tabs, current, params }: OrderTabsProps) {
  return (
    <nav className={styles.tabs} aria-label="Estado de las comandas">
      {tabs.map((tab) => {
        const next = withFilter(params, "estado", tab.value);
        next.delete(ORDER_PARAM);
        return (
          <Link
            key={tab.value}
            className={styles.tab}
            to={{ search: next.toString() }}
            aria-current={tab.value === current ? "page" : undefined}
          >
            {tab.label} <b className={styles.count}>{tab.count}</b>
          </Link>
        );
      })}
    </nav>
  );
}
