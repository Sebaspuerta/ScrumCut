import type { ReactNode } from "react";

import type { CashState } from "../api/types";
import { openedSince } from "../lib/format";
import { PageTitle } from "../ui/PageTitle";
import { Pill } from "../ui/Pill";

interface CashTitleProps {
  state: CashState;
  timeZone: string;
  actions: ReactNode;
}

function subtitle(state: CashState, timeZone: string): string {
  if (state.needs_branch) return "Todas las sedes";
  const session = state.session;
  if (session === null) return `Sede ${state.branch ?? ""} · sin caja abierta`;
  return `Sede ${state.branch ?? ""} · ${openedSince(session.opened_at, state.today, timeZone)} · abrió ${session.opened_by}`;
}

/** «Abierta», la sede, desde cuándo y quién la abrió (Caja.dc.html en la identidad R1). */
export function CashTitle({ state, timeZone, actions }: CashTitleProps) {
  return (
    <PageTitle
      actions={actions}
      eyebrow={state.branch ? `Operación · ${state.branch}` : "Operación"}
      title="Caja"
      subtitle={
        <>
          {state.session && <Pill tone="positive">Abierta</Pill>}
          <span>{subtitle(state, timeZone)}</span>
        </>
      }
    />
  );
}
