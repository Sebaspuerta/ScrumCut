import { useState } from "react";
import { useSearchParams } from "react-router";

import { StatusMessage } from "../frame/StatusMessage";
import { useMe } from "../hooks/useMe";
import { useReceivables } from "../hooks/useReceivables";
import { RECEIVABLE_PARAM } from "../lib/appRoutes";
import { listQuery, withParam } from "../lib/searchParams";
import { Notice } from "../ui/Notice";
import { AgingStrip } from "./AgingStrip";
import { PortfolioStrip } from "./PortfolioStrip";
import { ReceivableDetailPanel } from "./ReceivableDetailPanel";
import { ReceivableListPanel } from "./ReceivableListPanel";
import { FILTER_KEYS } from "./receivableParams";
import styles from "./Receivables.module.css";
import { ReceivablesTitle } from "./ReceivablesTitle";

/** Fiados: la cartera de la sede, la antigüedad, la lista por urgencia y el abono del elegido. Todo va en la URL. */
export function ReceivablesPage() {
  const me = useMe();
  const [params, setParams] = useSearchParams();
  const [paid, setPaid] = useState<string | null>(null);
  const permissions = me.data?.permissions ?? [];
  const allowed = permissions.includes("fiados.ver");
  const receivables = useReceivables(listQuery(params, FILTER_KEYS), allowed);
  const selected = params.get(RECEIVABLE_PARAM);
  const branch = me.data?.branch?.current_label ?? "";
  if (!allowed) return <StatusMessage kind="empty">Tu rol no tiene acceso a los fiados.</StatusMessage>;
  const list = receivables.data;
  return (
    <>
      <ReceivablesTitle branch={branch} canPay={permissions.includes("fiados.abonar")} paying={selected !== null} />
      {paid && <Notice>{paid}</Notice>}
      {list && <PortfolioStrip portfolio={list.portfolio} today={list.today} />}
      {list && <AgingStrip aging={list.aging} total={list.portfolio.pending.total} />}
      <div className={styles.split}>
        <ReceivableListPanel
          query={receivables}
          selected={selected}
          branch={branch}
          params={params}
          onParams={setParams}
        />
        {selected ? (
          <ReceivableDetailPanel
            key={selected}
            id={selected}
            onPaid={setPaid}
            onClose={() => {
              setPaid(null);
              setParams(withParam(params, RECEIVABLE_PARAM, null));
            }}
          />
        ) : (
          <section className={styles.panel} aria-label="Detalle del fiado">
            <p className={styles.muted}>Elige un fiado de la lista para ver sus abonos y registrar uno.</p>
          </section>
        )}
      </div>
    </>
  );
}
