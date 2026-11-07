import { Button } from "../ui/Button";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";

interface ConfirmProductDialogProps {
  title: string;
  message: string;
  confirmLabel: string;
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

/** La confirmación antes de desactivar o borrar un producto: qué pasa con él y qué queda. */
export function ConfirmProductDialog({
  title,
  message,
  confirmLabel,
  busy,
  error,
  onCancel,
  onConfirm,
}: ConfirmProductDialogProps) {
  return (
    <FormDialog title={title} onClose={onCancel}>
      <div className={form.form}>
        <p>{message}</p>
        <FormAlert message={error} />
        <div className={form.actions}>
          <Button kind="secondary" onClick={onCancel}>
            Cancelar
          </Button>
          <Button data-autofocus disabled={busy} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </FormDialog>
  );
}
