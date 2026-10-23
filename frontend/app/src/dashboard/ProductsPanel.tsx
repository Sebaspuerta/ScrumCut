import type { Dashboard } from "../api/types";
import { formatCop } from "../lib/format";
import { Panel } from "../ui/Panel";
import table from "../ui/Table.module.css";

interface ProductsPanelProps {
  products: Dashboard["products"];
}

/** Los cinco productos más vendidos del mes, con su margen sobre el costo copiado al cerrar. */
export function ProductsPanel({ products }: ProductsPanelProps) {
  return (
    <Panel title="Productos más vendidos" subtitle="Unidades, ventas y margen del mes">
      {products.length === 0 ? (
        <p className={table.empty}>Todavía no se han vendido productos este mes.</p>
      ) : (
        <table className={table.table}>
          <thead>
            <tr>
              <th scope="col">Producto</th>
              <th scope="col" className={table.num}>
                Unidades
              </th>
              <th scope="col" className={table.num}>
                Ventas
              </th>
              <th scope="col" className={table.num}>
                Margen
              </th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <tr key={product.name}>
                <td>{product.name}</td>
                <td className={table.num}>{product.units}</td>
                <td className={table.num}>{formatCop(product.sales)}</td>
                <td className={table.num}>{product.margin === null ? "—" : `${product.margin} %`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
