import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { OrderDetail } from "../api/types";
import { useMoneyMutation } from "../hooks/useMoneyMutation";
import { Button } from "../ui/Button";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";
import { ClientPicker } from "./ClientPicker";
import styles from "./OrderDetail.module.css";

interface ChangeClientDialogProps {
  order: OrderDetail;
  onClose: () => void;
}

/** Cambia el cliente de una comanda abierta o la deja de mostrador (sin cliente no puede quedar como fiado). */
export function ChangeClientDialog({ order, onClose }: ChangeClientDialogProps) {
  const change = useMoneyMutation((client: string | null) =>
    api.post("/api/v1/orders/{public_id}/client/", { client }, { public_id: order.id }),
  );
  const errors = formErrors(change.error);
  return (
    <FormDialog title="Cambiar cliente" subtitle={`Comanda #${String(order.number)}`} onClose={onClose}>
      <div className={styles.dialogBody}>
        <ClientPicker
          selected={null}
          onPick={(client) => {
            change.submit(client.id, onClose);
          }}
        />
        <FormAlert message={errors.fields.client ?? errors.detail} />
        {order.client && (
          <Button
            kind="secondary"
            disabled={change.isPending}
            onClick={() => {
              change.submit(null, onClose);
            }}
          >
            Dejar como cliente de mostrador
          </Button>
        )}
      </div>
    </FormDialog>
  );
}
