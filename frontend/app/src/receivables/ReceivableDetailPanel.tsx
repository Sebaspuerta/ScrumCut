import { StatusMessage } from "../frame/StatusMessage";
import { useReceivable } from "../hooks/useReceivables";
import { ReceivableProfile } from "./ReceivableProfile";
import styles from "./Receivables.module.css";

interface ReceivableDetailPanelProps {
  id: string;
  onPaid: (message: string) => void;
  onClose: () => void;
}

/** El fiado elegido con sus estados de carga y error (uno de otra sede no se encuentra). */
export function ReceivableDetailPanel({ id, onPaid, onClose }: ReceivableDetailPanelProps) {
  const receivable = useReceivable(id);
  if (receivable.isPending || receivable.isError) {
    return (
      <section className={styles.panel} aria-label="Detalle del fiado">
        {receivable.isPending ? (
          <StatusMessage kind="loading">Cargando el fiado…</StatusMessage>
        ) : (
          <StatusMessage kind="error" onRetry={() => void receivable.refetch()}>
            No pudimos cargar este fiado. Si es de otra sede, elígela en la barra superior.
          </StatusMessage>
        )}
      </section>
    );
  }
  return <ReceivableProfile receivable={receivable.data} onPaid={onPaid} onClose={onClose} />;
}
