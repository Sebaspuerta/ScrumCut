import { useId } from "react";

import type { OrderDetail } from "../api/types";
import { StatusMessage } from "../frame/StatusMessage";
import { useOrder } from "../hooks/useOrders";
import { AddLineForm } from "./AddLineForm";
import { CancelOrder } from "./CancelOrder";
import { CheckoutForm } from "./CheckoutForm";
import styles from "./OrderDetail.module.css";
import { OrderHead } from "./OrderHead";
import { OrderLines } from "./OrderLines";
import { OrderPayments } from "./OrderPayments";
import { OrderTotals } from "./OrderTotals";

interface OrderDetailPanelProps {
  id: string;
  onClose: () => void;
}

function Receipt({ order, onClose }: { order: OrderDetail; onClose: () => void }) {
  const titleId = useId();
  return (
    <section className={styles.panel} aria-labelledby={titleId}>
      <OrderHead order={order} titleId={titleId} onClose={onClose} />
      <OrderLines order={order} />
      {order.actions.edit && <AddLineForm orderId={order.id} />}
      <OrderTotals order={order} />
      {order.payments.length > 0 && <OrderPayments order={order} />}
      {order.actions.checkout && <CheckoutForm order={order} />}
      {order.actions.cancel && <CancelOrder order={order} />}
    </section>
  );
}

/** La comanda elegida (el comprobante de la referencia), con sus estados de carga y error. */
export function OrderDetailPanel({ id, onClose }: OrderDetailPanelProps) {
  const order = useOrder(id);
  if (order.isPending) {
    return (
      <section className={styles.panel} aria-label="Detalle de la comanda">
        <StatusMessage kind="loading">Cargando la comanda…</StatusMessage>
      </section>
    );
  }
  if (order.isError) {
    return (
      <section className={styles.panel} aria-label="Detalle de la comanda">
        <StatusMessage kind="error" onRetry={() => void order.refetch()}>
          No pudimos cargar esta comanda.
        </StatusMessage>
      </section>
    );
  }
  return <Receipt order={order.data} onClose={onClose} />;
}
