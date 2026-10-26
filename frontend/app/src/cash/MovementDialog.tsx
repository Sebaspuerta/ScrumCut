import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { CashState, ManualKind } from "../api/types";
import { useMoneyMutation } from "../hooks/useMoneyMutation";
import { cx } from "../lib/cx";
import { MAX_LENGTH } from "../lib/fieldLimits";
import { digitsOnly } from "../lib/money";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";
import input from "../ui/Input.module.css";

interface MovementDialogProps {
  state: CashState;
  session: string;
  initialKind: string;
  onClose: () => void;
}

/** Gasto, retiro o ingreso en efectivo de la caja abierta (la de otro día lo rechaza en el servidor). */
export function MovementDialog({ state, session, initialKind, onClose }: MovementDialogProps) {
  const options = state.manual_kinds;
  const [kind, setKind] = useState(options.find((option) => option.value === initialKind)?.value ?? "gasto");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const save = useMoneyMutation(() =>
    api.post("/api/v1/cash/{session}/movements/", { kind: kind as ManualKind, amount, description }, { session }),
  );
  const errors = formErrors(save.error);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    save.submit(undefined, onClose);
  };
  return (
    <FormDialog title="Registrar movimiento" subtitle="En efectivo, de la caja abierta" onClose={onClose}>
      <form className={form.form} onSubmit={submit}>
        <Field label="Tipo" error={errors.fields.kind}>
          {(control) => (
            <select
              {...control}
              className={input.input}
              value={kind}
              onChange={(event) => {
                setKind(event.target.value);
              }}
            >
              {options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field label="Monto" error={errors.fields.amount}>
          {(control) => (
            <input
              {...control}
              data-autofocus
              className={cx(input.input, input.figure)}
              inputMode="numeric"
              required
              value={amount}
              onChange={(event) => {
                setAmount(digitsOnly(event.target.value));
              }}
            />
          )}
        </Field>
        <Field label="Concepto" error={errors.fields.description}>
          {(control) => (
            <input
              {...control}
              className={input.input}
              required
              maxLength={MAX_LENGTH.ManualMovementRequest.description}
              value={description}
              onChange={(event) => {
                setDescription(event.target.value);
              }}
            />
          )}
        </Field>
        <FormAlert message={errors.detail} />
        <div className={form.actions}>
          <Button kind="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={save.isPending || amount === "" || description.trim() === ""}>
            Registrar
          </Button>
        </div>
      </form>
    </FormDialog>
  );
}
