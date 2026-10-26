import { useSearchParams } from "react-router";

import type { CashSession, CashState } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { clock, countOf, formatCop, outflowCop, signedCop } from "../lib/format";
import input from "../ui/Input.module.css";
import { Panel } from "../ui/Panel";
import table from "../ui/Table.module.css";
import styles from "./Cash.module.css";

interface MovementsPanelProps {
  state: CashState;
  session: CashSession;
}

function KindFilter({ state }: { state: CashState }) {
  const [params, setParams] = useSearchParams();
  return (
    <label className={styles.filter}>
      <span>Tipo</span>
      <select
        className={input.input}
        value={state.kind}
        onChange={(event) => {
          const next = new URLSearchParams(params);
          if (event.target.value) next.set("tipo", event.target.value);
          else next.delete("tipo");
          setParams(next);
        }}
      >
        {state.kinds.map((kind) => (
          <option key={kind.value} value={kind.value}>
            {kind.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function OtherMedia({ session }: { session: CashSession }) {
  const { transfers, credit } = session.other_media;
  return (
    <div className={styles.otherMedia}>
      <span className={styles.label}>Otros medios · no entran a la caja física</span>
      <p>
        <strong>{formatCop(transfers.total)}</strong> en transferencias y otros medios ·{" "}
        {countOf(transfers.count, "pago", "pagos")} · <strong>{formatCop(credit.total)}</strong> en fiados nuevos ·{" "}
        {countOf(credit.count, "comanda", "comandas")}
      </p>
    </div>
  );
}

/** Todo lo que entra o sale de la caja física, con su filtro por tipo y, debajo, lo que no entra a ella. */
export function MovementsPanel({ state, session }: MovementsPanelProps) {
  const timeZone = useTimeZone();
  return (
    <Panel
      title="Movimientos de hoy"
      subtitle="Todo lo que entra o sale de la caja física, en orden."
      actions={<KindFilter state={state} />}
      className={styles.history}
    >
      <div className={styles.scroll}>
        <table className={table.table}>
          <thead>
            <tr>
              <th scope="col">Hora</th>
              <th scope="col">Tipo</th>
              <th scope="col">Concepto</th>
              <th scope="col">Registró</th>
              <th scope="col" className={table.num}>
                Monto
              </th>
            </tr>
          </thead>
          <tbody>
            {session.movements.map((movement) => (
              <tr key={movement.id}>
                <td>{clock(movement.at, timeZone)}</td>
                <td>{movement.kind_label}</td>
                <td>{movement.description}</td>
                <td>{movement.by}</td>
                <td className={table.num}>
                  {movement.direction === "out" ? outflowCop(movement.amount) : signedCop(movement.amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {session.movements.length === 0 && (
          <p className={table.empty}>Sin movimientos{state.kind ? " de este tipo" : ""} todavía.</p>
        )}
      </div>
      <OtherMedia session={session} />
    </Panel>
  );
}
