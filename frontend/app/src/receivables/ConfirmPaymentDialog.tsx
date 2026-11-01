import { Button } from "../ui/Button";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";

interface ConfirmPaymentDialogProps {
  summary: string;
  after: string;
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

/** Confirmación antes de abonar: el abono mueve la caja y no se edita después. */
export function ConfirmPaymentDialog({ summary, after, busy, error, onCancel, onConfirm }: ConfirmPaymentDialogProps) {
  return (
    <FormDialog title="¿Registrar el abono?" onClose={onCancel}>
      <div className={form.form}>
        <p>{summary}</p>
        <p>{after}</p>
        <FormAlert message={error} />
        <div className={form.actions}>
          <Button kind="secondary" onClick={onCancel}>
            Volver
          </Button>
          <Button data-autofocus disabled={busy} onClick={onConfirm}>
            {busy ? "Registrando…" : "Sí, registrar el abono"}
          </Button>
        </div>
      </div>
    </FormDialog>
  );
}
