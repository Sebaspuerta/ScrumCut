import { Plus, Zap } from "lucide-react";

import { DJANGO_ROUTES } from "../lib/djangoRoutes";
import { longDate } from "../lib/format";
import { Button, buttonClass } from "../ui/Button";
import { PageTitle } from "../ui/PageTitle";

interface OrdersTitleProps {
  branch: string;
  day: string | null;
  canCreate: boolean;
  canQuickCharge: boolean;
  onCreate: () => void;
}

/** «Sede … · fecha · precios de la sede …», con Cobro rápido (aún en Django) y Nueva comanda. */
export function OrdersTitle({ branch, day, canCreate, canQuickCharge, onCreate }: OrdersTitleProps) {
  const subtitle = [`Sede ${branch}`, day ? longDate(day) : null, canCreate ? `precios de la sede ${branch}` : null];
  return (
    <PageTitle
      eyebrow="Operación"
      title="Comandas"
      subtitle={subtitle.filter(Boolean).join(" · ")}
      actions={
        <>
          {canQuickCharge && (
            <a className={buttonClass("secondary")} href={DJANGO_ROUTES.quickCharge}>
              <Zap size={16} aria-hidden="true" />
              Cobro rápido
            </a>
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
