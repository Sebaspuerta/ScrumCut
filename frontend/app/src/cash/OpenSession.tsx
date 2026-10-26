import type { CashSession, CashState, Closing } from "../api/types";
import { COUNT_ANCHOR } from "../lib/appRoutes";
import { buttonClass } from "../ui/Button";
import { Notice } from "../ui/Notice";
import styles from "./Cash.module.css";
import { CashStrip } from "./CashStrip";
import { CountPanel } from "./CountPanel";
import { MovementsPanel } from "./MovementsPanel";

interface OpenSessionProps {
  state: CashState;
  session: CashSession;
  onClosed: (closing: Closing) => void;
}

const STALE =
  "Esta caja viene de otro día. Ciérrala con su arqueo y abre la de hoy: no recibe efectivo ni gastos hasta entonces.";

/** La caja abierta: el aviso si viene de otro día, la franja del día, los movimientos y el arqueo. */
export function OpenSession({ state, session, onClosed }: OpenSessionProps) {
  return (
    <>
      {session.stale && (
        <Notice
          action={
            state.actions.close && (
              <a className={buttonClass("text")} href={`#${COUNT_ANCHOR}`}>
                Cerrarla ahora
              </a>
            )
          }
        >
          {STALE}
        </Notice>
      )}
      <CashStrip session={session} />
      <div className={styles.columns}>
        <MovementsPanel state={state} session={session} />
        {state.actions.close && <CountPanel state={state} session={session} onClosed={onClosed} />}
      </div>
    </>
  );
}
