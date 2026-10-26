import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import { useMoneyMutation } from "../hooks/useMoneyMutation";
import { cx } from "../lib/cx";
import { digitsOnly } from "../lib/money";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import input from "../ui/Input.module.css";
import { Panel } from "../ui/Panel";

/** Abrir la caja de la sede con su base: el efectivo con el que empieza el día. */
export function OpenCashForm() {
  const [base, setBase] = useState("");
  const open = useMoneyMutation(() => api.post("/api/v1/cash/open/", { opening_amount: base }));
  const errors = formErrors(open.error);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    open.submit(undefined);
  };
  return (
    <Panel title="Abrir caja" subtitle="La base es el efectivo con el que empieza el día.">
      <form className={form.form} onSubmit={submit} aria-label="Abrir caja">
        <Field label="Base de apertura" error={errors.fields.opening_amount}>
          {(control) => (
            <input
              {...control}
              className={cx(input.input, input.figure)}
              inputMode="numeric"
              required
              value={base}
              onChange={(event) => {
                setBase(digitsOnly(event.target.value));
              }}
            />
          )}
        </Field>
        <FormAlert message={errors.detail} />
        <div className={form.actions}>
          <Button type="submit" disabled={open.isPending || base === ""}>
            Abrir caja
          </Button>
        </div>
      </form>
    </Panel>
  );
}
