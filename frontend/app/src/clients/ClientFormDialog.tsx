import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { ClientDetail, DataPolicy } from "../api/types";
import { useWriteMutation } from "../hooks/useWriteMutation";
import { Button } from "../ui/Button";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";
import { initialDraft, toCreate, toUpdate, type ClientDraft } from "./clientDraft";
import { ClientFields } from "./ClientFields";
import { ConsentField } from "./ConsentField";

type Target = { client: ClientDetail } | { policy: DataPolicy };

interface ClientFormDialogProps {
  target: Target;
  onClose: () => void;
  onSaved: (client: ClientDetail) => void;
}

const POSSIBLE_DUPLICATE = "possible_duplicate";

function save(target: Target, draft: ClientDraft): Promise<ClientDetail> {
  if ("client" in target) {
    return api.post("/api/v1/clients/{public_id}/edit/", toUpdate(draft), { public_id: target.client.id });
  }
  return api.post("/api/v1/clients/create/", toCreate(draft));
}

/** Nuevo cliente (con la autorización de la política vigente) o editar sus datos. Un posible duplicado por nombre
 * se confirma marcando que es otra persona. */
export function ClientFormDialog({ target, onClose, onSaved }: ClientFormDialogProps) {
  const editing = "client" in target ? target.client : null;
  const [draft, setDraft] = useState(() => initialDraft(editing));
  const mutation = useWriteMutation(() => save(target, draft));
  const errors = formErrors(mutation.error);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    mutation.submit(undefined, onSaved);
  };
  const missingConsent = "policy" in target && !draft.consent;
  return (
    <FormDialog
      title={editing ? `Editar a ${editing.name}` : "Nuevo cliente"}
      subtitle="Los datos de la persona son de la barbería: cualquier sede la encuentra."
      onClose={onClose}
    >
      <form className={form.form} onSubmit={submit} aria-label="Datos del cliente">
        <ClientFields
          draft={draft}
          errors={errors}
          editing={editing !== null}
          onChange={(field, value) => {
            setDraft({ ...draft, [field]: value });
          }}
        />
        {"policy" in target && (
          <ConsentField
            policy={target.policy}
            checked={draft.consent}
            error={errors.fields.consent}
            onChange={(consent) => {
              setDraft({ ...draft, consent });
            }}
          />
        )}
        <FormAlert message={errors.detail} />
        {errors.code === POSSIBLE_DUPLICATE && (
          <label className={form.check}>
            <input
              type="checkbox"
              checked={draft.other_person}
              onChange={(event) => {
                setDraft({ ...draft, other_person: event.target.checked });
              }}
            />
            Es otra persona con el mismo nombre
          </label>
        )}
        <div className={form.actions}>
          <Button kind="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending || draft.full_name.trim() === "" || missingConsent}>
            {editing ? "Guardar cambios" : "Crear cliente"}
          </Button>
        </div>
      </form>
    </FormDialog>
  );
}
