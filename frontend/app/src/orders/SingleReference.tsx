import { Field } from "../ui/Field";
import type { CheckoutDraft } from "./checkoutDraft";
import styles from "./OrderDetail.module.css";
import { ReferenceInput } from "./ReferenceInput";

interface SingleReferenceProps {
  draft: CheckoutDraft;
  onChange: (draft: CheckoutDraft) => void;
}

/** La referencia de un pago con una sola forma que no es efectivo: no entra a la caja física. */
export function SingleReference({ draft, onChange }: SingleReferenceProps) {
  return (
    <Field
      label="Referencia del pago"
      hint="No entra a la caja física: queda en «otros medios» del cierre."
      className={styles.field}
    >
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
  );
}
