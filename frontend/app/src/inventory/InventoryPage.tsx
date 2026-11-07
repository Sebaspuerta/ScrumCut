import { useSearchParams } from "react-router";

import { StatusMessage } from "../frame/StatusMessage";
import { useProducts } from "../hooks/useInventory";
import { useMe } from "../hooks/useMe";
import { PRODUCT_PARAM } from "../lib/appRoutes";
import { cx } from "../lib/cx";
import { listQuery, withParam } from "../lib/searchParams";
import styles from "./Inventory.module.css";
import { InventoryDialogs } from "./InventoryDialogs";
import { CATEGORIES_PARAM, EDIT_PARAM, FILTER_KEYS, HISTORY_PARAM, MOVE_PARAM, NEW_PARAM } from "./inventoryParams";
import { InventoryTitle } from "./InventoryTitle";
import { ProductDetailPanel } from "./ProductDetailPanel";
import { ProductListPanel } from "./ProductListPanel";
import { StockAlerts } from "./StockAlerts";

const CATEGORY_PERMISSIONS = ["inventario.crear", "inventario.editar", "inventario.eliminar"];

/** Inventario: los avisos de la sede, el catálogo con su stock y precio, y el panel del producto. Todo en la URL. */
export function InventoryPage() {
  const me = useMe();
  const [params, setParams] = useSearchParams();
  const permissions = me.data?.permissions ?? [];
  const allowed = permissions.includes("inventario.ver");
  const products = useProducts(listQuery(params, FILTER_KEYS), allowed);
  const selected = params.get(PRODUCT_PARAM);
  const branchState = me.data?.branch;
  const allBranches = branchState?.mode === "todas";
  const branch = branchState?.current_label ?? "";
  const open = (key: string, value = "1") => {
    setParams(withParam(params, key, value));
  };
  if (!allowed) return <StatusMessage kind="empty">Tu rol no tiene acceso al inventario.</StatusMessage>;
  return (
    <>
      <InventoryTitle
        branch={branch}
        canCreate={permissions.includes("inventario.crear")}
        canManageCategories={CATEGORY_PERMISSIONS.some((code) => permissions.includes(code))}
        onCreate={() => {
          open(NEW_PARAM);
        }}
        onCategories={() => {
          open(CATEGORIES_PARAM);
        }}
      />
      <StockAlerts />
      <div className={styles.split}>
        <ProductListPanel
          query={products}
          selected={selected}
          branch={branch}
          allBranches={allBranches}
          params={params}
          onParams={setParams}
        />
        {selected ? (
          <ProductDetailPanel
            key={selected}
            id={selected}
            onEdit={() => {
              open(EDIT_PARAM);
            }}
            onMove={(move) => {
              open(MOVE_PARAM, move);
            }}
            onClose={() => {
              setParams(withParam(withParam(params, PRODUCT_PARAM, null), HISTORY_PARAM, null));
            }}
          />
        ) : (
          <section className={cx(styles.panel, styles.idle)} aria-label="Producto">
            <p className={styles.muted}>Elige un producto de la lista para ver su stock, precio y movimientos.</p>
          </section>
        )}
      </div>
      <InventoryDialogs
        list={products.data}
        selected={selected}
        branch={allBranches ? null : branch}
        permissions={permissions}
        params={params}
        onParams={setParams}
      />
    </>
  );
}
