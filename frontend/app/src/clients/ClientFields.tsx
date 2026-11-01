import type { FormErrors } from "../api/errors";
import { MAX_LENGTH } from "../lib/fieldLimits";
import { Field } from "../ui/Field";
import form from "../ui/Form.module.css";
import input from "../ui/Input.module.css";
import type { ClientDraft, TextField } from "./clientDraft";

interface ClientFieldsProps {
  draft: ClientDraft;
  errors: FormErrors;
  editing: boolean;
  onChange: (field: TextField, value: string) => void;
}

const KEEP_HINT = "Déjalo vacío para no cambiarlo.";

/** Nombre, celular, cédula, correo y preferencias: los datos de la persona, que son de la barbería. */
export function ClientFields({ draft, errors, editing, onChange }: ClientFieldsProps) {
  const text = (field: TextField) => ({
    value: draft[field],
    onChange: (event: { target: { value: string } }) => {
      onChange(field, event.target.value);
    },
  });
  return (
    <>
      <Field label="Nombre completo" error={errors.fields.full_name}>
        {(control) => (
          <input
            {...control}
            {...text("full_name")}
            data-autofocus
            className={input.input}
            required
            maxLength={MAX_LENGTH.ClientRequest.full_name}
          />
        )}
      </Field>
      <div className={form.row}>
        <Field label="Celular" error={errors.fields.phone} hint={editing ? KEEP_HINT : undefined}>
          {(control) => (
            <input
              {...control}
              {...text("phone")}
              className={input.input}
              inputMode="tel"
              maxLength={MAX_LENGTH.ClientRequest.phone}
            />
          )}
        </Field>
        <Field label="Cédula" error={errors.fields.document} hint={editing ? KEEP_HINT : undefined}>
          {(control) => (
            <input
              {...control}
              {...text("document")}
              className={input.input}
              maxLength={MAX_LENGTH.ClientRequest.document}
            />
          )}
        </Field>
      </div>
      <Field label="Correo" error={errors.fields.email}>
        {(control) => (
          <input
            {...control}
            {...text("email")}
            className={input.input}
            type="email"
            maxLength={MAX_LENGTH.ClientRequest.email}
          />
        )}
      </Field>
      <Field label="Preferencias y notas" error={errors.fields.notes}>
        {(control) => (
          <textarea
            {...control}
            {...text("notes")}
            className={input.input}
            rows={3}
            maxLength={MAX_LENGTH.ClientRequest.notes}
          />
        )}
      </Field>
    </>
  );
}
