import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { CategoryRef } from "../api/types";
import { useWriteMutation } from "../hooks/useWriteMutation";
import { MAX_LENGTH } from "../lib/fieldLimits";
import { Button } from "../ui/Button";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import input from "../ui/Input.module.css";
import styles from "./Inventory.module.css";

interface CategoryRowProps {
  category: CategoryRef;
  canRename: boolean;
  canDelete: boolean;
}

type CategoryChange = { name: string } | { delete_products: boolean };

function change(id: string, next: CategoryChange) {
  if ("name" in next) return api.post("/api/v1/inventory/categories/{public_id}/edit/", next, { public_id: id });
  return api.post("/api/v1/inventory/categories/{public_id}/delete/", next, { public_id: id });
}

/** Una categoría: renombrarla y borrarla; al borrar se elige si sus productos quedan sin categoría o se borran. */
export function CategoryRow({ category, canRename, canDelete }: CategoryRowProps) {
  const [name, setName] = useState(category.name);
  const [withProducts, setWithProducts] = useState(false);
  const mutation = useWriteMutation((next: CategoryChange) => change(category.id, next));
  const errors = formErrors(mutation.error);
  const rename = (event: SubmitEvent) => {
    event.preventDefault();
    mutation.submit({ name });
  };
  return (
    <li>
      <form className={styles.categoryRow} onSubmit={rename} aria-label={`Categoría ${category.name}`}>
        <input
          aria-label="Nombre de la categoría"
          aria-invalid={Boolean(errors.fields.name)}
          className={input.input}
          disabled={!canRename}
          maxLength={MAX_LENGTH.CategoryRequest.name}
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
        />
        {canRename && (
          <Button type="submit" kind="secondary" disabled={mutation.isPending || name.trim() === category.name}>
            Renombrar
          </Button>
        )}
        {canDelete && (
          <>
            <label className={form.check}>
              <input
                type="checkbox"
                checked={withProducts}
                onChange={(event) => {
                  setWithProducts(event.target.checked);
                }}
              />
              Borrar también sus productos
            </label>
            <Button
              kind="secondary"
              disabled={mutation.isPending}
              onClick={() => {
                mutation.submit({ delete_products: withProducts });
              }}
            >
              Borrar
            </Button>
          </>
        )}
      </form>
      <FormAlert message={errors.fields.name ?? errors.detail} />
    </li>
  );
}
