import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { OrderCatalog, OrderDetail, QuickChargeRequest } from "../api/types";
import { StatusMessage } from "../frame/StatusMessage";
import { useWriteMutation } from "../hooks/useWriteMutation";
import { formatCop } from "../lib/format";
import { Button } from "../ui/Button";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import styles from "./QuickCharge.module.css";
import { QuickChargeFields } from "./QuickChargeFields";
import { initialQuickCharge, nextQuickCharge, shownPrice, toQuickChargeRequest } from "./quickChargeDraft";

interface QuickChargeFormProps {
  catalog: OrderCatalog;
  onClose: () => void;
}

/** La llave de un intento de cobro: la misma en cada reintento, una nueva después de cobrar. */
const newRequestKey = () => crypto.randomUUID();

function chargeLabel(pending: boolean, price: string | null): string {
  if (pending) return "Cobrando…";
  return price === null ? "Cobrar" : `Cobrar ${formatCop(price)}`;
}

/** Un corte o un producto cobrado completo. Tras cobrar avisa y queda listo para el siguiente. */
export function QuickChargeForm({ catalog, onClose }: QuickChargeFormProps) {
  const [draft, setDraft] = useState(() => initialQuickCharge(catalog));
  const [requestKey, setRequestKey] = useState(newRequestKey);
  const [charged, setCharged] = useState<OrderDetail | null>(null);
  const charge = useWriteMutation((request: QuickChargeRequest) => api.post("/api/v1/orders/quick-charge/", request));
  const errors = formErrors(charge.error);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    setCharged(null);
    charge.submit(toQuickChargeRequest(draft, requestKey), (order) => {
      setCharged(order);
      setDraft(nextQuickCharge);
      setRequestKey(newRequestKey());
    });
  };
  if (catalog.barbers.length === 0) {
    return <StatusMessage kind="empty">No hay barberos activos en esta sede para cobrar.</StatusMessage>;
  }
  return (
    <form className={form.form} onSubmit={submit} aria-label="Cobro rápido">
      {charged && (
        <p className={styles.done} role="status">
          Comanda #{charged.number} cobrada: {formatCop(charged.total)}.
        </p>
      )}
      <QuickChargeFields catalog={catalog} draft={draft} errors={errors.fields} onChange={setDraft} />
      <FormAlert message={errors.detail} />
      <div className={form.actions}>
        <Button kind="secondary" onClick={onClose}>
          Cerrar
        </Button>
        <Button type="submit" disabled={charge.isPending || draft.item === ""}>
          {chargeLabel(charge.isPending, shownPrice(catalog, draft.item))}
        </Button>
      </div>
    </form>
  );
}
