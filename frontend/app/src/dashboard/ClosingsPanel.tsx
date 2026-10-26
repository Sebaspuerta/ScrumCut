import type { Dashboard } from "../api/types";
import { formatCop, shortDate } from "../lib/format";
import { Difference } from "../ui/Difference";
import { Panel } from "../ui/Panel";
import table from "../ui/Table.module.css";

interface ClosingsPanelProps {
  closings: Dashboard["closings"];
}

export function ClosingsPanel({ closings }: ClosingsPanelProps) {
  return (
    <Panel title="Últimos cierres" subtitle="Esperado, contado y diferencia de cada arqueo">
      {closings.length === 0 ? (
        <p className={table.empty}>Todavía no hay cierres de caja.</p>
      ) : (
        <table className={table.table}>
          <thead>
            <tr>
              <th scope="col">Día</th>
              <th scope="col" className={table.num}>
                Esperado
              </th>
              <th scope="col" className={table.num}>
                Contado
              </th>
              <th scope="col" className={table.num}>
                Diferencia
              </th>
            </tr>
          </thead>
          <tbody>
            {closings.map((closing, index) => (
              <tr key={`${closing.date}-${String(index)}`}>
                <td>{shortDate(closing.date)}</td>
                <td className={table.num}>{formatCop(closing.expected)}</td>
                <td className={table.num}>{formatCop(closing.counted)}</td>
                <td className={table.num}>
                  <Difference value={closing.difference} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
