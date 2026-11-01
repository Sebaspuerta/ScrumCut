import type { OrderList, OrderTab } from "../api/types";
import { ORDER_PARAM } from "../lib/appRoutes";
import { withFilter } from "../lib/searchParams";
import { TabLinks } from "../ui/TabLinks";

interface OrderTabsProps {
  tabs: OrderList["tabs"];
  current: OrderTab;
  params: URLSearchParams;
}

/** Abiertas, Cerradas y Anuladas con su conteo; cambiar de pestaña cierra la comanda abierta. */
export function OrderTabs({ tabs, current, params }: OrderTabsProps) {
  const searchFor = (value: string) => {
    const next = withFilter(params, "estado", value);
    next.delete(ORDER_PARAM);
    return next.toString();
  };
  return <TabLinks tabs={tabs} current={current} label="Estado de las comandas" searchFor={searchFor} />;
}
