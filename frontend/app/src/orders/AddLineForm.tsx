import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import { useMoneyMutation } from "../hooks/useMoneyMutation";
import { useOrderCatalog } from "../hooks/useOrders";
import { cx } from "../lib/cx";
import { Button } from "../ui/Button";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { EMPTY_LINE, toNewLine } from "./lineDraft";
import { LineInputs } from "./LineInputs";
import styles from "./OrderDetail.module.css";

interface AddLineFormProps {
  orderId: string;
}

/** «Agregar servicio o producto» con su barbero: el precio lo pone el servidor con el de la sede. */
export function AddLineForm({ orderId }: AddLineFormProps) {
  const catalog = useOrderCatalog();
  const [draft, setDraft] = useState(EMPTY_LINE);
  const add = useMoneyMutation(() =>
    api.post("/api/v1/orders/{public_id}/lines/", toNewLine(draft), { public_id: orderId }),
  );
  const errors = formErrors(add.error);
  if (!catalog.data || catalog.data.needs_branch) return null;
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    add.submit(undefined, () => {
      setDraft(EMPTY_LINE);
    });
  };
  return (
    <form className={cx(form.form, styles.section)} onSubmit={submit} aria-label="Agregar servicio o producto">
      <LineInputs
        catalog={catalog.data}
        draft={draft}
        errors={errors.fields}
        defaultBarber="El de la comanda"
        onChange={setDraft}
      />
      <FormAlert message={errors.detail} />
      <div className={form.actions}>
        <Button kind="secondary" type="submit" disabled={add.isPending || draft.item === ""}>
          Agregar
        </Button>
      </div>
    </form>
  );
}
