import { Link } from "react-router";

import type { InventoryProduct } from "../api/types";
import { PRODUCT_PARAM } from "../lib/appRoutes";
import { cx } from "../lib/cx";
import { formatCop } from "../lib/format";
import { withParam } from "../lib/searchParams";
import { Pill } from "../ui/Pill";
import table from "../ui/Table.module.css";
import styles from "./Inventory.module.css";
import { ProductThumb } from "./ProductThumb";

interface ProductTableProps {
  rows: InventoryProduct[];
  selected: string | null;
  params: URLSearchParams;
  branch: string;
  allBranches: boolean;
}

function Stock({ row, allBranches }: { row: InventoryProduct; allBranches: boolean }) {
  if (!allBranches) return <b>{row.stock}</b>;
  return (
    <span className={styles.levelsCell}>
      <b>{row.stock}</b>
      {row.levels.map((level) => (
        <small key={level.branch}>
          {level.branch}: {level.quantity}
        </small>
      ))}
    </span>
  );
}

interface RowProps {
  row: InventoryProduct;
  selected: boolean;
  params: URLSearchParams;
  allBranches: boolean;
}

function Row({ row, selected, params, allBranches }: RowProps) {
  return (
    <tr className={cx(selected && styles.current)}>
      <td>
        <Link
          className={styles.rowLink}
          to={{ search: withParam(params, PRODUCT_PARAM, row.id).toString() }}
          aria-current={selected ? "true" : undefined}
        >
          <ProductThumb photo={row.photo} />
          <span>
            <b>{row.name}</b>
            <small>
              {row.category ?? "Sin categoría"} · {row.type_label}
            </small>
          </span>
        </Link>
      </td>
      <td className={table.num}>
        <Stock row={row} allBranches={allBranches} />
      </td>
      <td className={cx(table.num, styles.wide)}>{formatCop(row.price)}</td>
      <td>
        {!row.is_active && <Pill>Inactivo</Pill>}
        {row.is_active && row.low_stock && <Pill tone="attention">Stock bajo</Pill>}
      </td>
    </tr>
  );
}

/** Producto (con su foto), existencia en la sede (o por sede en «todas»), precio efectivo y aviso de stock bajo. */
export function ProductTable({ rows, selected, params, branch, allBranches }: ProductTableProps) {
  if (rows.length === 0) {
    return <p className={styles.empty}>Ningún producto coincide. Revisa los filtros o crea uno nuevo.</p>;
  }
  return (
    <table className={table.table}>
      <caption className="visually-hidden">Productos de la sede {branch}</caption>
      <thead>
        <tr>
          <th scope="col">Producto</th>
          <th scope="col" className={table.num}>
            Stock
          </th>
          <th scope="col" className={cx(table.num, styles.wide)}>
            Precio
          </th>
          <th scope="col">
            <span className="visually-hidden">Aviso</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <Row key={row.id} row={row} selected={row.id === selected} params={params} allBranches={allBranches} />
        ))}
      </tbody>
    </table>
  );
}
