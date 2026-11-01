import { Button } from "../ui/Button";
import form from "../ui/Form.module.css";
import { FormDialog } from "../ui/FormDialog";

interface NoPolicyDialogProps {
  onClose: () => void;
}

/** Sin una política de tratamiento de datos publicada no se registran clientes (Ley 1581). */
export function NoPolicyDialog({ onClose }: NoPolicyDialogProps) {
  return (
    <FormDialog title="Nuevo cliente" onClose={onClose}>
      <div className={form.form}>
        <p role="status">
          No hay una política de tratamiento de datos publicada: sin ella no se pueden registrar clientes.
        </p>
        <div className={form.actions}>
          <Button kind="secondary" onClick={onClose}>
            Volver
          </Button>
        </div>
      </div>
    </FormDialog>
  );
}
