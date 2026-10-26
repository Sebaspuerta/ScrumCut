import { useState } from "react";
import { useSearchParams } from "react-router";

import type { CashState, Closing } from "../api/types";
import { StatusMessage } from "../frame/StatusMessage";
import { useCash } from "../hooks/useCash";
import { useMe, useTimeZone } from "../hooks/useMe";
import { REGISTER_PARAM } from "../lib/appRoutes";
import { formatCop } from "../lib/format";
import { Difference } from "../ui/Difference";
import { Notice } from "../ui/Notice";
import { CashActions } from "./CashActions";
import { CashTitle } from "./CashTitle";
import { ClosingsHistory } from "./ClosingsHistory";
import { MovementDialog } from "./MovementDialog";
import { OpenCashForm } from "./OpenCashForm";
import { OpenSession } from "./OpenSession";

function Closed({ closing }: { closing: Closing }) {
  return (
    <Notice>
      Caja cerrada con {formatCop(closing.counted)}. Diferencia: <Difference value={closing.difference} />
    </Notice>
  );
}

function Body({ state, onClosed }: { state: CashState; onClosed: (closing: Closing) => void }) {
  if (state.needs_branch) return <StatusMessage kind="empty">Elige una sede para ver su caja.</StatusMessage>;
  if (state.session === null) {
    return state.actions.open ? (
      <OpenCashForm />
    ) : (
      <StatusMessage kind="empty">No hay una caja abierta en esta sede.</StatusMessage>
    );
  }
  return <OpenSession state={state} session={state.session} onClosed={onClosed} />;
}

/** Caja de la sede: abrir, registrar movimientos y cerrar con el arqueo. En "todas" pide elegir una sede. */
export function CashPage() {
  const me = useMe();
  const timeZone = useTimeZone();
  const [params, setParams] = useSearchParams();
  const allowed = me.data?.permissions.includes("caja.ver") ?? false;
  const cash = useCash(params.get("tipo") ?? "", allowed);
  const [closed, setClosed] = useState<Closing | null>(null);
  if (!allowed) return <StatusMessage kind="empty">Tu rol no tiene acceso a la caja.</StatusMessage>;
  if (cash.isPending) return <StatusMessage kind="loading">Cargando la caja…</StatusMessage>;
  if (cash.isError) {
    return (
      <StatusMessage kind="error" onRetry={() => void cash.refetch()}>
        No pudimos cargar la caja.
      </StatusMessage>
    );
  }
  const state = cash.data;
  const register = params.get(REGISTER_PARAM);
  const setRegister = (kind: string | null) => {
    const next = new URLSearchParams(params);
    if (kind === null) next.delete(REGISTER_PARAM);
    else next.set(REGISTER_PARAM, kind);
    setParams(next);
  };
  return (
    <>
      <CashTitle state={state} timeZone={timeZone} actions={<CashActions state={state} onRegister={setRegister} />} />
      {closed && <Closed closing={closed} />}
      <Body state={state} onClosed={setClosed} />
      {!state.needs_branch && <ClosingsHistory />}
      {register !== null && state.session && state.actions.movement && (
        <MovementDialog
          state={state}
          session={state.session.id}
          initialKind={register}
          onClose={() => {
            setRegister(null);
          }}
        />
      )}
    </>
  );
}
