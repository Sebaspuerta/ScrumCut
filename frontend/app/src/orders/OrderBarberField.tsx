import type { OrderCatalog } from "../api/types";
import { Field } from "../ui/Field";
import input from "../ui/Input.module.css";

interface OrderBarberFieldProps {
  catalog: OrderCatalog;
  value: string;
  error: string | undefined;
  onChange: (barber: string) => void;
}

/** El barbero principal de la comanda; sin elegir, el servidor deja al barbero que la abre (si lo es). */
export function OrderBarberField({ catalog, value, error, onChange }: OrderBarberFieldProps) {
  return (
    <Field label="Barbero" error={error}>
      {(control) => (
        <select
          {...control}
          className={input.input}
          value={value}
          onChange={(event) => {
            onChange(event.target.value);
          }}
        >
          <option value="">Sin barbero por ahora</option>
          {catalog.barbers.map((barber) => (
            <option key={barber.id} value={barber.id}>
              {barber.name}
            </option>
          ))}
        </select>
      )}
    </Field>
  );
}
