import type { ProductDetail } from "../api/types";
import { Pill } from "../ui/Pill";
import styles from "./Inventory.module.css";

/** Las existencias en cada sede del alcance, con el aviso de las que están en o bajo el mínimo. */
export function StockLevels({ product }: { product: ProductDetail }) {
  return (
    <>
      <h3 className={styles.subhead}>Stock por sede</h3>
      {product.levels.length === 0 ? (
        <p className={styles.muted}>Todavía no hay existencias de este producto en la sede.</p>
      ) : (
        <ul className={styles.lines}>
          {product.levels.map((level) => (
            <li key={level.branch} className={styles.line}>
              <span>{level.branch}</span>
              <span className={styles.figure}>
                {level.low && <Pill tone="attention">Stock bajo</Pill>} <b>{level.quantity}</b>
              </span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
