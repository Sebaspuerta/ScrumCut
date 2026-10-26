import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { CashSession, CashState, Closing } from "../api/types";
import { useMoneyMutation } from "../hooks/useMoneyMutation";
import { COUNT_ANCHOR } from "../lib/appRoutes";
import { formatCop } from "../lib/format";
import { fromCents, isZeroAmount } from "../lib/money";
import { Button } from "../ui/Button";
import { Difference } from "../ui/Difference";
import { FormAlert } from "../ui/FormAlert";
import styles from "./Cash.module.css";
import { CloseConfirmDialog } from "./CloseConfirmDialog";
import { countedCents, EMPTY_COUNT, previewDifference, toCloseRequest } from "./countDraft";
import { CountInputs } from "./CountInputs";

interface CountPanelProps {
  state: CashState;
  session: CashSession;
  onClosed: (closing: Closing) => void;
}

/** Arqueo por denominación: el contado y la diferencia se ven al contar; con diferencia, la nota es obligatoria. */
export function CountPanel({ state, session, onClosed }: CountPanelProps) {
  const [draft, setDraft] = useState(EMPTY_COUNT);
  const [confirming, setConfirming] = useState(false);
  const close = useMoneyMutation(() =>
    api.post("/api/v1/cash/{session}/close/", toCloseRequest(draft, state.denominations), { session: session.id }),
  );
  const errors = formErrors(close.error);
  const counted = formatCop(fromCents(countedCents(draft, state.denominations)));
  const difference = previewDifference(draft, state.denominations, session.expected);
  const hasDifference = !isZeroAmount(difference);
  const needsNote = hasDifference && draft.notes.trim() === "";
  const ask = (event: SubmitEvent) => {
    event.preventDefault();
    setConfirming(true);
  };
  return (
    <section id={COUNT_ANCHOR} className={styles.count} aria-labelledby="titulo-arqueo">
      <h2 id="titulo-arqueo" className={styles.title}>
        Arqueo y cierre
      </h2>
      <p className={styles.muted}>Cuenta el efectivo por denominación. El sistema suma solo.</p>
      <form onSubmit={ask} aria-label="Arqueo de la caja">
        <CountInputs
          state={state}
          draft={draft}
          errors={errors.fields}
          hasDifference={hasDifference}
          onChange={setDraft}
        />
        <dl className={styles.totals}>
          <div>
            <dt>Esperado en caja</dt>
            <dd>{formatCop(session.expected)}</dd>
          </div>
          <div className={styles.grand}>
            <dt>Contado</dt>
            <dd>{counted}</dd>
          </div>
        </dl>
        <p className={styles.difference} aria-live="polite">
          <span>Diferencia</span>
          <b>
            <Difference value={difference} explained />
          </b>
        </p>
        <FormAlert message={errors.detail} />
        <Button type="submit" block disabled={close.isPending || needsNote}>
          Cerrar caja con {counted}
        </Button>
        <p className={styles.muted}>Al cerrar, la caja queda bloqueada y el cierre queda en la auditoría.</p>
      </form>
      {confirming && (
        <CloseConfirmDialog
          counted={counted}
          difference={difference}
          busy={close.isPending}
          onCancel={() => {
            setConfirming(false);
          }}
          onConfirm={() => {
            setConfirming(false);
            close.submit(undefined, onClosed);
          }}
        />
      )}
    </section>
  );
}
