import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { ProductDetail } from "../api/types";
import { useWriteMutation } from "../hooks/useWriteMutation";
import { cx } from "../lib/cx";
import { formatCop } from "../lib/format";
import { asTyped, digitsOnly } from "../lib/money";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import { FormAlert } from "../ui/FormAlert";
import input from "../ui/Input.module.css";
import styles from "./Inventory.module.css";

type PriceChange = { price: string } | null;

function change(product: ProductDetail, next: PriceChange): Promise<ProductDetail> {
  const params = { public_id: product.id };
  if (next === null) return api.post("/api/v1/inventory/products/{public_id}/branch-price/remove/", undefined, params);
  return api.post("/api/v1/inventory/products/{public_id}/branch-price/", next, params);
}

/** El precio de venta propio de la sede (Dueño y Administrador); sin él rige el del catálogo. */
export function BranchPriceForm({ product }: { product: ProductDetail }) {
  const [price, setPrice] = useState(() => (product.branch_price === null ? "" : asTyped(product.branch_price)));
  const mutation = useWriteMutation((next: PriceChange) => change(product, next));
  const errors = formErrors(mutation.error);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    mutation.submit({ price });
  };
  return (
    <form onSubmit={submit} aria-label="Precio de la sede">
      <h3 className={styles.subhead}>Precio propio en {product.branch}</h3>
      <div className={styles.priceRow}>
        <Field
          label="Precio de venta en la sede"
          error={errors.fields.price}
          hint={`Catálogo: ${formatCop(product.sale_price)}`}
        >
          {(control) => (
            <input
              {...control}
              className={cx(input.input, input.figure)}
              inputMode="numeric"
              value={price}
              onChange={(event) => {
                setPrice(digitsOnly(event.target.value));
              }}
            />
          )}
        </Field>
        <Button type="submit" disabled={mutation.isPending || price === ""}>
          Guardar
        </Button>
        {product.branch_price !== null && (
          <Button
            kind="secondary"
            disabled={mutation.isPending}
            onClick={() => {
              mutation.submit(null, () => {
                setPrice("");
              });
            }}
          >
            Quitar
          </Button>
        )}
      </div>
      <FormAlert message={errors.detail} />
    </form>
  );
}
