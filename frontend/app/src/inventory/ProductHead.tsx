import { Pencil, X } from "lucide-react";

import type { ProductDetail } from "../api/types";
import { Button } from "../ui/Button";
import { Pill } from "../ui/Pill";
import styles from "./Inventory.module.css";
import { ProductThumb } from "./ProductThumb";

interface ProductHeadProps {
  product: ProductDetail;
  onEdit: () => void;
  onClose: () => void;
}

/** La foto, el nombre con su categoría y tipo, Editar (con inventario.editar) y cerrar el panel. */
export function ProductHead({ product, onEdit, onClose }: ProductHeadProps) {
  return (
    <div className={styles.head}>
      <ProductThumb photo={product.photo} large />
      <div className={styles.identity}>
        <h2 className={styles.name}>{product.name}</h2>
        <p className={styles.muted}>
          {product.category?.name ?? "Sin categoría"} · {product.type_label}
        </p>
        {!product.is_active && <Pill>Inactivo</Pill>}
      </div>
      <div className={styles.headActions}>
        {product.actions.edit && (
          <Button kind="secondary" onClick={onEdit}>
            <Pencil size={16} aria-hidden="true" />
            Editar
          </Button>
        )}
        <button type="button" className={styles.close} aria-label="Cerrar el producto" onClick={onClose}>
          <X size={20} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
