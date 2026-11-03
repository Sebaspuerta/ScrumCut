import type { FormErrors } from "../api/errors";
import type { OrderCatalog } from "../api/types";
import { Field } from "../ui/Field";
import input from "../ui/Input.module.css";
import { PayMethods } from "../ui/PayMethods";
import { ItemOptions } from "./ItemOptions";
import { takesReference, type QuickChargeDraft } from "./quickChargeDraft";
import { ReferenceInput } from "./ReferenceInput";

interface QuickChargeFieldsProps {
  catalog: OrderCatalog;
  draft: QuickChargeDraft;
  errors: FormErrors["fields"];
  onChange: (draft: QuickChargeDraft) => void;
}

/** Qué se cobra, quién lo hizo y cómo se paga; la referencia solo en un pago que no es en efectivo. */
export function QuickChargeFields({ catalog, draft, errors, onChange }: QuickChargeFieldsProps) {
  return (
    <>
      <Field label="Servicio o producto" error={errors.item}>
        {(control) => (
          <select
            {...control}
            data-autofocus
            className={input.input}
            value={draft.item}
            onChange={(event) => {
              onChange({ ...draft, item: event.target.value });
            }}
          >
            <ItemOptions catalog={catalog} />
          </select>
        )}
      </Field>
      <Field label="Barbero" error={errors.barber}>
        {(control) => (
          <select
            {...control}
            className={input.input}
            value={draft.barber}
            onChange={(event) => {
              onChange({ ...draft, barber: event.target.value });
            }}
          >
            {catalog.barbers.map((barber) => (
              <option key={barber.id} value={barber.id}>
                {barber.name}
              </option>
            ))}
          </select>
        )}
      </Field>
      <PayMethods
        value={draft.method}
        methods={catalog.methods}
        error={errors.method}
        onChange={(method) => {
          onChange({ ...draft, method });
        }}
      />
      {takesReference(draft) && (
        <Field label="Referencia del pago" error={errors.reference}>
          {(control) => (
            <ReferenceInput
              {...control}
              value={draft.reference}
              onChange={(reference) => {
                onChange({ ...draft, reference });
              }}
            />
          )}
        </Field>
      )}
    </>
  );
}
