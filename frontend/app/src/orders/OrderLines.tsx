import { X } from "lucide-react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { OrderDetail, OrderLine } from "../api/types";
import { useMoneyMutation } from "../hooks/useMoneyMutation";
import { formatCop } from "../lib/format";
import { FormAlert } from "../ui/FormAlert";
import styles from "./OrderDetail.module.css";

interface OrderLinesProps {
  order: OrderDetail;
}

function lineNote(line: OrderLine): string {
  const each = line.quantity > 1 ? `${String(line.quantity)} × ${formatCop(line.unit_price)}` : null;
  const barber = line.barber ?? (line.kind === "servicio" ? "Sin barbero" : null);
  return [line.kind_label, barber, each].filter(Boolean).join(" · ");
}

/** Las líneas: ítem, tipo, barbero, cantidad y total; mientras esté abierta, cada una se puede quitar. */
export function OrderLines({ order }: OrderLinesProps) {
  const remove = useMoneyMutation((item: string) =>
    api.post("/api/v1/orders/{public_id}/lines/{item}/remove/", undefined, { public_id: order.id, item }),
  );
  if (order.lines.length === 0) return <p className={styles.muted}>Todavía no tiene líneas.</p>;
  return (
    <>
      <ul className={styles.lines} aria-label="Líneas de la comanda">
        {order.lines.map((line) => (
          <li key={line.id} className={styles.line}>
            <span className={styles.lineText}>
              <b>{line.name}</b>
              <small>{lineNote(line)}</small>
            </span>
            <b className={styles.figure}>{formatCop(line.line_total)}</b>
            {order.actions.edit && (
              <button
                type="button"
                className={styles.remove}
                aria-label={`Quitar ${line.name}`}
                disabled={remove.isPending}
                onClick={() => {
                  remove.submit(line.id);
                }}
              >
                <X size={16} aria-hidden="true" />
              </button>
            )}
          </li>
        ))}
      </ul>
      <FormAlert message={formErrors(remove.error).detail} />
    </>
  );
}
