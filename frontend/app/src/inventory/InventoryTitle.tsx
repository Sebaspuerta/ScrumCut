import { Plus, Tags } from "lucide-react";

import { Button } from "../ui/Button";
import { PageTitle } from "../ui/PageTitle";

interface InventoryTitleProps {
  branch: string;
  canCreate: boolean;
  canManageCategories: boolean;
  onCreate: () => void;
  onCategories: () => void;
}

/** «Sede … · existencias, precio y movimientos de cada producto», con Categorías y Nuevo producto. */
export function InventoryTitle({
  branch,
  canCreate,
  canManageCategories,
  onCreate,
  onCategories,
}: InventoryTitleProps) {
  return (
    <PageTitle
      eyebrow="Catálogo"
      title="Inventario"
      subtitle={`Sede ${branch} · existencias, precio y movimientos de cada producto`}
      actions={
        <>
          {canManageCategories && (
            <Button kind="secondary" onClick={onCategories}>
              <Tags size={16} aria-hidden="true" />
              Categorías
            </Button>
          )}
          {canCreate && (
            <Button onClick={onCreate}>
              <Plus size={16} aria-hidden="true" />
              Nuevo producto
            </Button>
          )}
        </>
      }
    />
  );
}
