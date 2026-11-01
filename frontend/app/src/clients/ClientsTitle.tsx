import { Plus } from "lucide-react";

import { Button } from "../ui/Button";
import { PageTitle } from "../ui/PageTitle";

interface ClientsTitleProps {
  branch: string;
  canCreate: boolean;
  onCreate: () => void;
}

/** «Sede … · nivel e historial de cada cliente en esta sede», con Nuevo cliente. */
export function ClientsTitle({ branch, canCreate, onCreate }: ClientsTitleProps) {
  return (
    <PageTitle
      eyebrow="Clientes"
      title="Clientes"
      subtitle={`Sede ${branch} · nivel e historial de cada cliente en esta sede`}
      actions={
        canCreate && (
          <Button onClick={onCreate}>
            <Plus size={16} aria-hidden="true" />
            Nuevo cliente
          </Button>
        )
      }
    />
  );
}
