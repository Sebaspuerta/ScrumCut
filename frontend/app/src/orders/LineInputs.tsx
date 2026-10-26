import type { OrderCatalog } from "../api/types";
import type { FormErrors } from "../api/errors";
import { formatCop } from "../lib/format";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import input from "../ui/Input.module.css";
import { itemValue, PRODUCT, SERVICE, type LineDraft } from "./lineDraft";

interface LineInputsProps {
  catalog: OrderCatalog;
  draft: LineDraft;
  errors: FormErrors["fields"];
  /** Lo que dice el barbero vacío: el de la comanda o ninguno. */
  defaultBarber: string;
  onChange: (draft: LineDraft) => void;
}

/** Servicio o producto (con el precio y el stock de la sede), barbero de la línea y cantidad. */
export function LineInputs({ catalog, draft, errors, defaultBarber, onChange }: LineInputsProps) {
  const itemError = errors.service ?? errors.product ?? errors.lines;
  return (
    <div className={form.row}>
      <Field label="Servicio o producto" error={itemError}>
        {(control) => (
          <select
            {...control}
            className={input.input}
            value={draft.item}
            onChange={(event) => {
              onChange({ ...draft, item: event.target.value });
            }}
          >
            <option value="">Elige un servicio o un producto</option>
            <optgroup label="Servicios">
              {catalog.services.map((service) => (
                <option key={service.id} value={itemValue(SERVICE, service.id)}>
                  {service.name} · {formatCop(service.price)}
                </option>
              ))}
            </optgroup>
            <optgroup label="Productos">
              {catalog.products.map((product) => (
                <option key={product.id} value={itemValue(PRODUCT, product.id)}>
                  {product.name} · {formatCop(product.price)} · {product.stock} en stock
                </option>
              ))}
            </optgroup>
          </select>
        )}
      </Field>
      <Field label="Barbero de la línea" error={errors.barber}>
        {(control) => (
          <select
            {...control}
            className={input.input}
            value={draft.barber}
            onChange={(event) => {
              onChange({ ...draft, barber: event.target.value });
            }}
          >
            <option value="">{defaultBarber}</option>
            {catalog.barbers.map((barber) => (
              <option key={barber.id} value={barber.id}>
                {barber.name}
              </option>
            ))}
          </select>
        )}
      </Field>
      <Field label="Cantidad" error={errors.quantity}>
        {(control) => (
          <input
            {...control}
            className={input.input}
            type="number"
            inputMode="numeric"
            min={1}
            max={catalog.max_quantity}
            value={draft.quantity}
            onChange={(event) => {
              onChange({ ...draft, quantity: event.target.value });
            }}
          />
        )}
      </Field>
    </div>
  );
}
