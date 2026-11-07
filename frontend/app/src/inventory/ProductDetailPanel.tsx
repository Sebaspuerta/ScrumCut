import { useSearchParams } from "react-router";

import { LoadError } from "../frame/LoadError";
import { StatusMessage } from "../frame/StatusMessage";
import { useProduct } from "../hooks/useInventory";
import { withParam } from "../lib/searchParams";
import { BranchPriceForm } from "./BranchPriceForm";
import styles from "./Inventory.module.css";
import { HISTORY_PARAM, type Move } from "./inventoryParams";
import { MovementHistory } from "./MovementHistory";
import { ProductFacts } from "./ProductFacts";
import { ProductHead } from "./ProductHead";
import { ProductStatus } from "./ProductStatus";
import { StockLevels } from "./StockLevels";
import { StockMoves } from "./StockMoves";

interface ProductDetailPanelProps {
  id: string;
  onEdit: () => void;
  onMove: (move: Move) => void;
  onClose: () => void;
}

/** El producto elegido: acciones del día, datos, precio y stock de la sede, y su historial paginado. */
export function ProductDetailPanel({ id, onEdit, onMove, onClose }: ProductDetailPanelProps) {
  const [params, setParams] = useSearchParams();
  const product = useProduct(id, params.get(HISTORY_PARAM) ?? "1");
  const data = product.data;
  return (
    <section className={styles.panel} aria-label="Producto" aria-busy={product.isFetching}>
      {product.isPending && <StatusMessage kind="loading">Cargando el producto…</StatusMessage>}
      {product.isError && (
        <LoadError error={product.error} onRetry={() => void product.refetch()}>
          No pudimos cargar el producto.
        </LoadError>
      )}
      {data && (
        <>
          <ProductHead product={data} onEdit={onEdit} onClose={onClose} />
          <StockMoves product={data} onMove={onMove} />
          <ProductFacts product={data} />
          <StockLevels product={data} />
          {data.actions.branch_price && <BranchPriceForm key={data.branch_price ?? ""} product={data} />}
          <MovementHistory
            product={data}
            onPage={(page) => {
              setParams(withParam(params, HISTORY_PARAM, String(page)));
            }}
          />
          <ProductStatus product={data} onDeleted={onClose} />
        </>
      )}
    </section>
  );
}
