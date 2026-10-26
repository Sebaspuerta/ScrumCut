import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { OrderDetail } from "../api/types";
import { useMoneyMutation } from "../hooks/useMoneyMutation";
import { MAX_LENGTH } from "../lib/fieldLimits";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";
import input from "../ui/Input.module.css";
import styles from "./OrderDetail.module.css";

interface CancelOrderProps {
  order: OrderDetail;
}

/** «Anular comanda» pide el motivo y una confirmación; una cerrada devuelve su dinero y su stock (el servidor). */
export function CancelOrder({ order }: CancelOrderProps) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const cancel = useMoneyMutation(() =>
    api.post("/api/v1/orders/{public_id}/cancel/", { reason }, { public_id: order.id }),
  );
  const errors = formErrors(cancel.error);
  const close = () => {
    setOpen(false);
  };
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    cancel.submit(undefined, close);
  };
  const closed = order.status === "cerrada";
  return (
    <>
      <Button
        kind="text"
        className={styles.center}
        onClick={() => {
          setOpen(true);
        }}
      >
        Anular comanda
      </Button>
      {open && (
        <FormDialog title={`Anular la comanda #${String(order.number)}`} onClose={close}>
          <form className={form.form} onSubmit={submit}>
            <p>
              {closed
                ? "Ya está cobrada: se devolverá su dinero desde la caja abierta y se restituirá el stock."
                : "Quedará anulada y no se podrá cobrar."}
            </p>
            <Field label="Motivo de la anulación" error={errors.fields.reason}>
              {(control) => (
                <textarea
                  {...control}
                  data-autofocus
                  className={input.input}
                  rows={3}
                  maxLength={MAX_LENGTH.CancelRequest.reason}
                  required
                  value={reason}
                  onChange={(event) => {
                    setReason(event.target.value);
                  }}
                />
              )}
            </Field>
            <FormAlert message={errors.detail} />
            <div className={form.actions}>
              <Button kind="secondary" onClick={close}>
                Volver
              </Button>
              <Button type="submit" disabled={cancel.isPending || reason.trim() === ""}>
                Anular comanda
              </Button>
            </div>
          </form>
        </FormDialog>
      )}
    </>
  );
}
