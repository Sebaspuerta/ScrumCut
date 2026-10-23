import { DJANGO_ROUTES } from "../lib/djangoRoutes";
import { buttonClass } from "../ui/Button";
import styles from "./StaleCashNotice.module.css";

/** La caja de la sede viene de otro día: se cierra con su arqueo en Caja antes de abrir la de hoy. */
export function StaleCashNotice() {
  return (
    <div className={styles.notice} role="status">
      <span>Esta caja viene de otro día. Ciérrala con su arqueo y abre la de hoy.</span>
      <a className={buttonClass("text")} href={DJANGO_ROUTES.cash}>
        Ir a caja
      </a>
    </div>
  );
}
