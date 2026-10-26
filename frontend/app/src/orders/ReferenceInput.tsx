import { MAX_LENGTH } from "../lib/fieldLimits";
import input from "../ui/Input.module.css";

interface ReferenceInputProps {
  value: string;
  onChange: (reference: string) => void;
  id?: string | undefined;
  "aria-label"?: string | undefined;
  "aria-describedby"?: string | undefined;
  "aria-invalid"?: boolean | undefined;
}

/** La referencia opcional de un pago que no es en efectivo (Nequi 4821), con el largo que acepta el servidor. */
export function ReferenceInput({ value, onChange, ...accessibility }: ReferenceInputProps) {
  return (
    <input
      {...accessibility}
      className={input.input}
      placeholder="Referencia (opcional)"
      maxLength={MAX_LENGTH.PaymentPartRequest.reference}
      value={value}
      onChange={(event) => {
        onChange(event.target.value);
      }}
    />
  );
}
