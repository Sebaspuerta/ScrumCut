import { Plus, Zap } from "lucide-react";

import { longDate } from "../lib/format";
import { Button } from "../ui/Button";
import { PageTitle } from "../ui/PageTitle";

interface OrdersTitleProps {
  branch: string;
  day: string | null;
  canCreate: boolean;
  canQuickCharge: boolean;
  onCreate: () => void;
  onQuickCharge: () => void;
}

/** «Sede … · fecha · precios de la sede …», con Cobro rápido y Nueva comanda. */
export function OrdersTitle({ branch, day, canCreate, canQuickCharge, onCreate, onQuickCharge }: OrdersTitleProps) {
  const subtitle = [`Sede ${branch}`, day ? longDate(day) : null, canCreate ? `precios de la sede ${branch}` : null];
  return (
    <PageTitle
      eyebrow="Operación"
      title="Comandas"
      subtitle={subtitle.filter(Boolean).join(" · ")}
      actions={
        <>
          {canQuickCharge && (
            <Button kind="secondary" onClick={onQuickCharge}>
              <Zap size={16} aria-hidden="true" />
              Cobro rápido
            </Button>
          )}
          {canCreate && (
            <Button onClick={onCreate}>
              <Plus size={16} aria-hidden="true" />
              Nueva comanda
            </Button>
          )}
        </>
      }
    />
  );
}
