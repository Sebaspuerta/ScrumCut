import type { Dashboard } from "../api/types";
import { formatCop } from "../lib/format";
import { Panel } from "../ui/Panel";
import table from "../ui/Table.module.css";

interface BarbersPanelProps {
  barbers: Dashboard["barbers"];
}

const initialsOf = (name: string) =>
  name
    .split(" ")
    .slice(0, 2)
    .map((word) => word.charAt(0))
    .join("")
    .toUpperCase();

/** Ventas netas y comisión de cada barbero en el mes, como quedaron al cerrar cada comanda. */
export function BarbersPanel({ barbers }: BarbersPanelProps) {
  return (
    <Panel title="Rendimiento por barbero" subtitle="Ventas y comisión del mes">
      {barbers.length === 0 ? (
        <p className={table.empty}>Todavía no hay ventas de barberos en este mes.</p>
      ) : (
        <table className={table.table}>
          <thead>
            <tr>
              <th scope="col">Barbero</th>
              <th scope="col" className={table.num}>
                Comandas
              </th>
              <th scope="col" className={table.num}>
                Ventas
              </th>
              <th scope="col" className={table.num}>
                Comisión
              </th>
            </tr>
          </thead>
          <tbody>
            {barbers.map((barber) => (
              <tr key={barber.name}>
                <td>
                  <span className={table.avatar} aria-hidden="true">
                    {initialsOf(barber.name)}
                  </span>
                  {barber.name}
                </td>
                <td className={table.num}>{barber.orders}</td>
                <td className={table.num}>{formatCop(barber.sales)}</td>
                <td className={table.num}>{formatCop(barber.commission)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
