import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import { useWriteMutation } from "../hooks/useWriteMutation";
import { MAX_LENGTH } from "../lib/fieldLimits";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import input from "../ui/Input.module.css";

/** Crear una categoría; el servidor rechaza un nombre repetido sin mayúsculas. */
export function NewCategoryForm() {
  const [name, setName] = useState("");
  const mutation = useWriteMutation(() => api.post("/api/v1/inventory/categories/create/", { name }));
  const errors = formErrors(mutation.error);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    mutation.submit(undefined, () => {
      setName("");
    });
  };
  return (
    <form className={form.form} onSubmit={submit} aria-label="Nueva categoría">
      <Field label="Nueva categoría" error={errors.fields.name}>
        {(control) => (
          <input
            {...control}
            data-autofocus
            className={input.input}
            required
            maxLength={MAX_LENGTH.CategoryRequest.name}
            value={name}
            onChange={(event) => {
              setName(event.target.value);
            }}
          />
        )}
      </Field>
      <FormAlert message={errors.detail} />
      <div className={form.actions}>
        <Button type="submit" disabled={mutation.isPending || name.trim() === ""}>
          Crear categoría
        </Button>
      </div>
    </form>
  );
}
