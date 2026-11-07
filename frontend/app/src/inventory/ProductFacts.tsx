import type { ProductDetail } from "../api/types";
import { formatCop, shortDate } from "../lib/format";
import styles from "./Inventory.module.css";

const EMPTY = "—";

/** Existencia y precio de la sede, costo, precio del catálogo, mínimo, vencimiento y proveedor. */
export function ProductFacts({ product }: { product: ProductDetail }) {
  const where = product.branch ?? "todas las sedes";
  const facts: [string, string][] = [
    [`Stock en ${where}`, String(product.stock)],
    [product.branch ? `Precio en ${product.branch}` : "Precio del catálogo", formatCop(product.price)],
    ["Costo de compra", formatCop(product.purchase_cost)],
    ["Precio del catálogo", formatCop(product.sale_price)],
    ["Stock mínimo", product.minimum_stock === null ? EMPTY : String(product.minimum_stock)],
    ["Vence", product.expiration_date ? shortDate(product.expiration_date) : EMPTY],
    ["Proveedor", product.supplier || EMPTY],
  ];
  return (
    <dl className={styles.facts}>
      {facts.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
