import { Button } from "../ui/Button";
import { Difference } from "../ui/Difference";
import form from "../ui/Form.module.css";
import { FormDialog } from "../ui/FormDialog";

interface CloseConfirmDialogProps {
  counted: string;
  difference: string;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

/** Confirmación antes de cerrar: después de cerrar, la caja queda bloqueada. */
export function CloseConfirmDialog({ counted, difference, busy, onCancel, onConfirm }: CloseConfirmDialogProps) {
  return (
    <FormDialog title="¿Cerrar la caja?" onClose={onCancel}>
      <div className={form.form}>
        <p>
          Contado: <b>{counted}</b>. Diferencia: <Difference value={difference} explained />
        </p>
        <p>Después de cerrar no se pueden registrar más movimientos en esta caja.</p>
        <div className={form.actions}>
          <Button kind="secondary" onClick={onCancel}>
            Volver al arqueo
          </Button>
          <Button data-autofocus disabled={busy} onClick={onConfirm}>
            Sí, cerrar la caja
          </Button>
        </div>
      </div>
    </FormDialog>
  );
}
