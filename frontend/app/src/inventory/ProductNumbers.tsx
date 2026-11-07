import type { FormErrors } from "../api/errors";
import { cx } from "../lib/cx";
import { MAX_VALUE } from "../lib/fieldLimits";
import { digitsOnly } from "../lib/money";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import input from "../ui/Input.module.css";
import type { ProductDraft, ProductTextField } from "./productDraft";

interface ProductNumbersProps {
  draft: ProductDraft;
  errors: FormErrors;
  /** Solo al crear: el stock inicial entra en la sede activa. */
  creating: boolean;
  branch: string | null;
  onChange: (draft: ProductDraft) => void;
}

interface NumberFieldProps extends Omit<ProductNumbersProps, "creating" | "branch"> {
  field: ProductTextField;
  label: string;
  hint?: string | undefined;
}

/** Pesos: solo dígitos, como en los demás montos de la app. */
function NumberField({ draft, errors, onChange, field, label, hint }: NumberFieldProps) {
  return (
    <Field label={label} error={errors.fields[field]} hint={hint}>
      {(control) => (
        <input
          {...control}
          className={cx(input.input, input.figure)}
          inputMode="numeric"
          value={draft[field]}
          onChange={(event) => {
            onChange({ ...draft, [field]: digitsOnly(event.target.value) });
          }}
        />
      )}
    </Field>
  );
}

interface UnitsFieldProps extends Omit<NumberFieldProps, "field"> {
  field: "minimum_stock" | "initial_stock";
}

/** Unidades: enteras, con el teclado numérico y el tope que publica el esquema. */
function UnitsField({ draft, errors, onChange, field, label, hint }: UnitsFieldProps) {
  return (
    <Field label={label} error={errors.fields[field]} hint={hint}>
      {(control) => (
        <input
          {...control}
          className={cx(input.input, input.figure)}
          type="number"
          inputMode="numeric"
          min={0}
          max={MAX_VALUE.ProductCreateRequest[field]}
          step={1}
          value={draft[field]}
          onChange={(event) => {
            onChange({ ...draft, [field]: digitsOnly(event.target.value) });
          }}
        />
      )}
    </Field>
  );
}

/** Costo, precio del catálogo, mínimo, vencimiento y, al crear, el stock inicial de la sede. */
export function ProductNumbers({ draft, errors, creating, branch, onChange }: ProductNumbersProps) {
  const shared = { draft, errors, onChange };
  const stockHint = branch ? `Entra en la sede ${branch}.` : "En «Todas las sedes» se crea sin stock.";
  return (
    <>
      <div className={form.row}>
        <NumberField {...shared} field="purchase_cost" label="Costo de compra" />
        <NumberField {...shared} field="sale_price" label="Precio de venta" hint="El de toda sede sin precio propio." />
      </div>
      <div className={form.row}>
        <UnitsField {...shared} field="minimum_stock" label="Stock mínimo" hint="Vacío: sin aviso de stock bajo." />
        <Field label="Vence" error={errors.fields.expiration_date} hint="Solo para perecederos.">
          {(control) => (
            <input
              {...control}
              type="date"
              className={input.input}
              value={draft.expiration_date}
              onChange={(event) => {
                onChange({ ...draft, expiration_date: event.target.value });
              }}
            />
          )}
        </Field>
      </div>
      {creating && <UnitsField {...shared} field="initial_stock" label="Stock inicial" hint={stockHint} />}
    </>
  );
}
