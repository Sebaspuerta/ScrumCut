import { useSearchParams } from "react-router";

import { StatusMessage } from "../frame/StatusMessage";
import { useClosings } from "../hooks/useCash";
import { useTimeZone } from "../hooks/useMe";
import { clock, dayLabel, formatCop, zonedDate } from "../lib/format";
import { Difference } from "../ui/Difference";
import { Pagination } from "../ui/Pagination";
import { Panel } from "../ui/Panel";
import table from "../ui/Table.module.css";
import styles from "./Cash.module.css";

const PAGE_PARAM = "pagina";

/** El historial de cierres de la sede, por páginas (?pagina=): esperado, contado, diferencia y nota. */
export function ClosingsHistory() {
  const timeZone = useTimeZone();
  const [params, setParams] = useSearchParams();
  const closings = useClosings(params.get(PAGE_PARAM) ?? "1");
  const when = (moment: string) => `${dayLabel(zonedDate(moment, timeZone))}, ${clock(moment, timeZone)}`;
  return (
    <Panel
      title="Cierres de la sede"
      subtitle="Esperado, contado y diferencia de cada arqueo"
      className={styles.history}
    >
      {closings.isPending && <StatusMessage kind="loading">Cargando los cierres…</StatusMessage>}
      {closings.isError && (
        <StatusMessage kind="error" onRetry={() => void closings.refetch()}>
          No pudimos cargar los cierres.
        </StatusMessage>
      )}
      {closings.data?.count === 0 && <p className={table.empty}>Todavía no hay cierres en esta sede.</p>}
      {closings.data && closings.data.count > 0 && (
        <div className={styles.scroll}>
          <table className={table.table}>
            <thead>
              <tr>
                <th scope="col">Fecha</th>
                <th scope="col">Cerró</th>
                <th scope="col" className={table.num}>
                  Esperado
                </th>
                <th scope="col" className={table.num}>
                  Contado
                </th>
                <th scope="col" className={table.num}>
                  Diferencia
                </th>
                <th scope="col">Nota</th>
              </tr>
            </thead>
            <tbody>
              {closings.data.results.map((closing) => (
                <tr key={closing.id}>
                  <td>{when(closing.closed_at)}</td>
                  <td>{closing.closed_by}</td>
                  <td className={table.num}>{formatCop(closing.expected)}</td>
                  <td className={table.num}>{formatCop(closing.counted)}</td>
                  <td className={table.num}>
                    <Difference value={closing.difference} />
                  </td>
                  <td>{closing.notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {closings.data && (
        <Pagination
          page={closings.data.page}
          pages={closings.data.pages}
          count={closings.data.count}
          pageSize={closings.data.page_size}
          label="Páginas de cierres"
          onPage={(page) => {
            const next = new URLSearchParams(params);
            next.set(PAGE_PARAM, String(page));
            setParams(next);
          }}
        />
      )}
    </Panel>
  );
}
