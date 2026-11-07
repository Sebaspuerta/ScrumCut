import type { ProductDetail } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { formatCop, shortDate, zonedDate } from "../lib/format";
import { Pagination } from "../ui/Pagination";
import styles from "./Inventory.module.css";

interface MovementHistoryProps {
  product: ProductDetail;
  onPage: (page: number) => void;
}

const signed = (quantity: number) => (quantity > 0 ? `+${String(quantity)}` : `−${String(-quantity)}`);

/** Los movimientos de las sedes del alcance, lo más reciente primero: tipo, cantidad, el antes y el después. */
export function MovementHistory({ product, onPage }: MovementHistoryProps) {
  const timeZone = useTimeZone();
  const { results, page, pages, count, page_size } = product.movements;
  return (
    <>
      <h3 className={styles.subhead}>Movimientos</h3>
      {results.length === 0 ? (
        <p className={styles.muted}>Sin movimientos en la sede.</p>
      ) : (
        <ul className={styles.lines}>
          {results.map((movement) => (
            <li key={movement.id} className={styles.line}>
              <span>
                <b>
                  {movement.kind_label} · {movement.reason}
                </b>
                <small>
                  {shortDate(zonedDate(movement.at, timeZone))} · {movement.branch} · {movement.by} · costo{" "}
                  {formatCop(movement.unit_cost)}
                </small>
              </span>
              <span className={styles.figure}>
                <b>{signed(movement.quantity)}</b>
                <small>
                  {movement.stock_before} → {movement.stock_after}
                </small>
              </span>
            </li>
          ))}
        </ul>
      )}
      <Pagination
        page={page}
        pages={pages}
        count={count}
        pageSize={page_size}
        label="Páginas de movimientos"
        onPage={onPage}
      />
    </>
  );
}
