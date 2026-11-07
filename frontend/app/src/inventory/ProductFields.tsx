import type { FormErrors } from "../api/errors";
import type { Option, ProductType } from "../api/types";
import { MAX_LENGTH } from "../lib/fieldLimits";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import input from "../ui/Input.module.css";
import type { ProductDraft, ProductTextField } from "./productDraft";

interface ProductFieldsProps {
  draft: ProductDraft;
  errors: FormErrors;
  categories: Option[];
  types: Option[];
  onChange: (draft: ProductDraft) => void;
}

/** Nombre, categoría, tipo y proveedor: los datos del catálogo común de la barbería. */
export function ProductFields({ draft, errors, categories, types, onChange }: ProductFieldsProps) {
  const text = (field: ProductTextField) => ({
    value: draft[field],
    onChange: (event: { target: { value: string } }) => {
      onChange({ ...draft, [field]: event.target.value });
    },
  });
  return (
    <>
      <Field label="Nombre" error={errors.fields.name}>
        {(control) => (
          <input
            {...control}
            {...text("name")}
            data-autofocus
            className={input.input}
            required
            maxLength={MAX_LENGTH.ProductRequest.name}
          />
        )}
      </Field>
      <div className={form.row}>
        <Field label="Categoría" error={errors.fields.category}>
          {(control) => (
            <select {...control} {...text("category")} className={input.input}>
              <option value="">Sin categoría</option>
              {categories.map((category) => (
                <option key={category.value} value={category.value}>
                  {category.label}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field label="Tipo" error={errors.fields.product_type}>
          {(control) => (
            <select
              {...control}
              className={input.input}
              value={draft.product_type}
              onChange={(event) => {
                onChange({ ...draft, product_type: event.target.value as ProductType });
              }}
            >
              {types.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          )}
        </Field>
      </div>
      <Field label="Proveedor" error={errors.fields.supplier}>
        {(control) => (
          <input
            {...control}
            {...text("supplier")}
            className={input.input}
            maxLength={MAX_LENGTH.ProductRequest.supplier}
          />
        )}
      </Field>
    </>
  );
}
