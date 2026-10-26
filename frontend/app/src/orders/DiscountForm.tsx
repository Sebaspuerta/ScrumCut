import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { OrderDetail } from "../api/types";
import { useMoneyMutation } from "../hooks/useMoneyMutation";
import { cx } from "../lib/cx";
import { MAX_LENGTH } from "../lib/fieldLimits";
import { digitsOnly, toCents } from "../lib/money";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import input from "../ui/Input.module.css";

interface DiscountFormProps {
  order: OrderDetail;
  onDone: () => void;
}

/** Monto y motivo: el límite (hasta el subtotal) y el motivo obligatorio los valida el servidor. */
export function DiscountForm({ order, onDone }: DiscountFormProps) {
  const [amount, setAmount] = useState(digitsOnly(order.discount.split(".")[0] ?? ""));
  const [reason, setReason] = useState(order.discount_reason);
  const save = useMoneyMutation(() =>
    api.post("/api/v1/orders/{public_id}/discount/", { amount, reason }, { public_id: order.id }),
  );
  const errors = formErrors(save.error);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    save.submit(undefined, onDone);
  };
  return (
    <form className={form.form} onSubmit={submit} aria-label="Aplicar descuento">
      <div className={form.row}>
        <Field label="Monto del descuento" error={errors.fields.amount}>
          {(control) => (
            <input
              {...control}
              data-autofocus
              className={cx(input.input, input.figure)}
              inputMode="numeric"
              value={amount}
              onChange={(event) => {
                setAmount(digitsOnly(event.target.value));
              }}
            />
          )}
        </Field>
        <Field label="Motivo" error={errors.fields.reason}>
          {(control) => (
            <input
              {...control}
              className={input.input}
              maxLength={MAX_LENGTH.DiscountRequest.reason}
              value={reason}
              onChange={(event) => {
                setReason(event.target.value);
              }}
            />
          )}
        </Field>
      </div>
      <FormAlert message={errors.detail} />
      <div className={form.actions}>
        <Button kind="secondary" onClick={onDone}>
          Cancelar
        </Button>
        <Button kind="secondary" type="submit" disabled={save.isPending || toCents(amount) === null}>
          Aplicar
        </Button>
      </div>
    </form>
  );
}
