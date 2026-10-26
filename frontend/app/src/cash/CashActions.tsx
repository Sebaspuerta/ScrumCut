import type { CashState } from "../api/types";
import { COUNT_ANCHOR } from "../lib/appRoutes";
import { Button, buttonClass } from "../ui/Button";

interface CashActionsProps {
  state: CashState;
  onRegister: (kind: string) => void;
}

const FIRST_KIND = "gasto";

/** «Registrar movimiento» solo en una caja de hoy; «Hacer arqueo y cerrar» lleva al arqueo. */
export function CashActions({ state, onRegister }: CashActionsProps) {
  if (state.session === null) return null;
  return (
    <>
      {state.actions.movement && (
        <Button
          kind="secondary"
          onClick={() => {
            onRegister(FIRST_KIND);
          }}
        >
          Registrar movimiento
        </Button>
      )}
      {state.actions.close && (
        <a className={buttonClass("primary")} href={`#${COUNT_ANCHOR}`}>
          Hacer arqueo y cerrar
        </a>
      )}
    </>
  );
}
