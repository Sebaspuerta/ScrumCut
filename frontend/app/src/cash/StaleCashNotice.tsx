import { Link } from "react-router";

import { CASH_PATH } from "../lib/appRoutes";
import { buttonClass } from "../ui/Button";
import { Notice } from "../ui/Notice";

/** La caja de la sede viene de otro día: se cierra con su arqueo en Caja antes de abrir la de hoy. */
export function StaleCashNotice() {
  return (
    <Notice
      action={
        <Link className={buttonClass("text")} to={CASH_PATH}>
          Ir a caja
        </Link>
      }
    >
      Esta caja viene de otro día. Ciérrala con su arqueo y abre la de hoy.
    </Notice>
  );
}
