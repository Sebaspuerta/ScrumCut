import { LoadError } from "../frame/LoadError";
import { StatusMessage } from "../frame/StatusMessage";
import { useOrderCatalog } from "../hooks/useOrders";
import { FormDialog } from "../ui/FormDialog";
import { QuickChargeForm } from "./QuickChargeForm";

interface QuickChargeDialogProps {
  onClose: () => void;
}

/** Cobro rápido (regla 17) en la sede activa, al precio vigente de la sede: sin cliente y sin fiado. */
export function QuickChargeDialog({ onClose }: QuickChargeDialogProps) {
  const catalog = useOrderCatalog();
  const branch = catalog.data?.branch;
  return (
    <FormDialog
      title="Cobro rápido"
      subtitle={branch ? `Sede ${branch} · precios de la sede` : undefined}
      onClose={onClose}
    >
      {catalog.isPending && <StatusMessage kind="loading">Cargando servicios y productos…</StatusMessage>}
      {catalog.isError && (
        <LoadError error={catalog.error} onRetry={() => void catalog.refetch()}>
          No pudimos cargar los servicios y productos.
        </LoadError>
      )}
      {catalog.data?.needs_branch && (
        <StatusMessage kind="empty">Elige una sede en la barra superior para cobrar.</StatusMessage>
      )}
      {catalog.data && !catalog.data.needs_branch && <QuickChargeForm catalog={catalog.data} onClose={onClose} />}
    </FormDialog>
  );
}
