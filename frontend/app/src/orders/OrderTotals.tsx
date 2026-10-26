import { useState } from "react";

import type { OrderDetail } from "../api/types";
import { cx } from "../lib/cx";
import { formatCop } from "../lib/format";
import { Button } from "../ui/Button";
import { DiscountForm } from "./DiscountForm";
import styles from "./OrderDetail.module.css";

interface OrderTotalsProps {
  order: OrderDetail;
}

/** Subtotal, descuento (con «Aplicar descuento» si el rol puede) y total, tal como los calcula el servidor. */
export function OrderTotals({ order }: OrderTotalsProps) {
  const [discounting, setDiscounting] = useState(false);
  const reason = order.discount_reason ? ` · ${order.discount_reason}` : "";
  return (
    <div className={styles.section}>
      <dl className={styles.totals}>
        <div className={styles.totalRow}>
          <dt>Subtotal</dt>
          <dd>{formatCop(order.subtotal)}</dd>
        </div>
        <div className={styles.totalRow}>
          <dt>Descuento{reason}</dt>
          <dd>{formatCop(order.discount)}</dd>
        </div>
        <div className={cx(styles.totalRow, styles.grand)}>
          <dt>Total</dt>
          <dd>{formatCop(order.total)}</dd>
        </div>
      </dl>
      {order.actions.discount && !discounting && (
        <Button
          kind="text"
          className={styles.inlineAction}
          onClick={() => {
            setDiscounting(true);
          }}
        >
          Aplicar descuento
        </Button>
      )}
      {discounting && (
        <DiscountForm
          order={order}
          onDone={() => {
            setDiscounting(false);
          }}
        />
      )}
    </div>
  );
}
