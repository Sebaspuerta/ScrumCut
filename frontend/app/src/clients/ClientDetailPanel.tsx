import { StatusMessage } from "../frame/StatusMessage";
import { useClient } from "../hooks/useClients";
import { ClientProfile } from "./ClientProfile";
import styles from "./Clients.module.css";

interface ClientDetailPanelProps {
  id: string;
  branch: string;
  onEdit: () => void;
  onClose: () => void;
}

/** La ficha del cliente elegido, con sus estados de carga y error. */
export function ClientDetailPanel({ id, branch, onEdit, onClose }: ClientDetailPanelProps) {
  const client = useClient(id);
  if (client.isPending || client.isError) {
    return (
      <section className={styles.panel} aria-label="Ficha del cliente">
        {client.isPending ? (
          <StatusMessage kind="loading">Cargando la ficha…</StatusMessage>
        ) : (
          <StatusMessage kind="error" onRetry={() => void client.refetch()}>
            No pudimos cargar esta ficha.
          </StatusMessage>
        )}
      </section>
    );
  }
  return <ClientProfile client={client.data} branch={branch} onEdit={onEdit} onClose={onClose} />;
}
