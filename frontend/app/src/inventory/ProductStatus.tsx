import { useState } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { ProductDetail } from "../api/types";
import { useWriteMutation } from "../hooks/useWriteMutation";
import { Button } from "../ui/Button";
import { FormAlert } from "../ui/FormAlert";
import { ConfirmProductDialog } from "./ConfirmProductDialog";
import styles from "./Inventory.module.css";

type StatusChange = "activar" | "desactivar" | "borrar";

interface ProductStatusProps {
  product: ProductDetail;
  /** Después de borrarlo: el panel se cierra, el producto ya no existe. */
  onDeleted: () => void;
}

function change(product: ProductDetail, next: StatusChange): Promise<unknown> {
  const params = { public_id: product.id };
  if (next === "borrar") return api.post("/api/v1/inventory/products/{public_id}/delete/", undefined, params);
  return api.post("/api/v1/inventory/products/{public_id}/active/", { active: next === "activar" }, params);
}

const CONFIRMATIONS: Record<Exclude<StatusChange, "activar">, { title: string; message: string; label: string }> = {
  desactivar: {
    title: "¿Desactivar el producto?",
    message: "Deja de ofrecerse en las comandas y sale de la lista de activos. Su stock y su historial quedan.",
    label: "Sí, desactivar",
  },
  borrar: {
    title: "¿Borrar el producto?",
    message: "Sale del catálogo de todas las sedes. Sus ventas y movimientos ya registrados quedan.",
    label: "Sí, borrar",
  },
};

/** Activar, desactivar (inventario.editar) y borrar (inventario.eliminar), cada uno solo si el servidor lo permite.
 * Desactivar y borrar piden confirmación. */
export function ProductStatus({ product, onDeleted }: ProductStatusProps) {
  const [asking, setAsking] = useState<keyof typeof CONFIRMATIONS | null>(null);
  const mutation = useWriteMutation((next: StatusChange) => change(product, next));
  const { edit, delete: remove } = product.actions;
  if (!edit && !remove) return null;
  const confirm = (next: StatusChange) => {
    mutation.submit(next, () => {
      setAsking(null);
      if (next === "borrar") onDeleted();
    });
  };
  const confirmation = asking ? CONFIRMATIONS[asking] : null;
  return (
    <>
      <h3 className={styles.subhead}>Estado del producto</h3>
      <div className={styles.statusActions}>
        {edit && product.is_active && (
          <Button
            kind="secondary"
            onClick={() => {
              setAsking("desactivar");
            }}
          >
            Desactivar
          </Button>
        )}
        {edit && !product.is_active && (
          <Button
            kind="secondary"
            disabled={mutation.isPending}
            onClick={() => {
              confirm("activar");
            }}
          >
            Activar
          </Button>
        )}
        {remove && (
          <Button
            kind="secondary"
            onClick={() => {
              setAsking("borrar");
            }}
          >
            Borrar
          </Button>
        )}
      </div>
      {asking === null && <FormAlert message={formErrors(mutation.error).detail} />}
      {asking && confirmation && (
        <ConfirmProductDialog
          title={confirmation.title}
          message={`${product.name}: ${confirmation.message}`}
          confirmLabel={confirmation.label}
          busy={mutation.isPending}
          error={formErrors(mutation.error).detail}
          onCancel={() => {
            setAsking(null);
          }}
          onConfirm={() => {
            confirm(asking);
          }}
        />
      )}
    </>
  );
}
