import { X } from "lucide-react";
import { useState } from "react";

import type { OrderDetail } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { clock } from "../lib/format";
import { Button } from "../ui/Button";
import { Pill } from "../ui/Pill";
import { ChangeClientDialog } from "./ChangeClientDialog";
import styles from "./OrderDetail.module.css";

const STATUS: Record<OrderDetail["status"], string> = {
  abierta: "Abierta",
  en_espera: "En espera",
  cerrada: "Cerrada",
  anulada: "Anulada",
};

interface OrderHeadProps {
  order: OrderDetail;
  titleId: string;
  onClose: () => void;
}

function clientNote(order: OrderDetail): string {
  const client = order.client;
  if (client === null) return "Sin cliente registrado · no puede quedar como fiado";
  const visits = client.visits === 1 ? "1 visita" : `${String(client.visits)} visitas`;
  const level = client.level ? `Cliente ${client.level.toLowerCase()} en ${order.branch}` : null;
  return [level, visits, client.phone].filter(Boolean).join(" · ");
}

/** Número, cliente, cuándo se abrió, su estado y «Cambiar cliente» mientras esté abierta. */
export function OrderHead({ order, titleId, onClose }: OrderHeadProps) {
  const timeZone = useTimeZone();
  const [changing, setChanging] = useState(false);
  const opened = [`Desde las ${clock(order.created_at, timeZone)}`, order.barber, `Sede ${order.branch}`];
  return (
    <div className={styles.head}>
      <div>
        <p className={styles.eyebrow}>Comanda #{order.number}</p>
        <h2 id={titleId} className={styles.client}>
          {order.client?.name ?? "Cliente de mostrador"}
        </h2>
        <p className={styles.muted}>{opened.filter(Boolean).join(" · ")}</p>
        <p className={styles.muted}>{clientNote(order)}</p>
        {order.actions.edit && (
          <Button
            kind="text"
            className={styles.inlineAction}
            onClick={() => {
              setChanging(true);
            }}
          >
            Cambiar cliente
          </Button>
        )}
      </div>
      <div className={styles.headSide}>
        <Pill tone={order.status === "cerrada" ? "neutral" : "positive"}>{STATUS[order.status]}</Pill>
        <button type="button" className={styles.close} aria-label="Cerrar el detalle" onClick={onClose}>
          <X size={18} aria-hidden="true" />
        </button>
      </div>
      {changing && (
        <ChangeClientDialog
          order={order}
          onClose={() => {
            setChanging(false);
          }}
        />
      )}
    </div>
  );
}
