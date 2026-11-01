import { Plus } from "lucide-react";
import { Link } from "react-router";

import { buttonClass } from "../ui/Button";
import { PageTitle } from "../ui/PageTitle";
import { PAYMENT_ANCHOR } from "./receivableParams";

interface ReceivablesTitleProps {
  branch: string;
  canPay: boolean;
  /** Con un fiado abierto, el botón lleva a su abono; sin él, a los pendientes para elegir uno. */
  paying: boolean;
}

/** «Sede … · lo que deben los clientes en esta sede y sus abonos», con Registrar abono. */
export function ReceivablesTitle({ branch, canPay, paying }: ReceivablesTitleProps) {
  const icon = <Plus size={16} aria-hidden="true" />;
  return (
    <PageTitle
      eyebrow="Clientes"
      title="Fiados"
      subtitle={`Sede ${branch} · lo que deben los clientes en esta sede y sus abonos`}
      actions={
        canPay &&
        (paying ? (
          <a className={buttonClass("primary")} href={`#${PAYMENT_ANCHOR}`}>
            {icon}
            Registrar abono
          </a>
        ) : (
          <Link className={buttonClass("primary")} to={{ search: "pestana=pendientes" }}>
            {icon}
            Registrar abono
          </Link>
        ))
      }
    />
  );
}
