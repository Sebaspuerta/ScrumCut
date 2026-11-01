// El formulario de cliente mientras se llena. Celular y cédula no se muestran al editar (el servidor los guarda
// normalizados y la cédula cifrada): vacíos, no cambian. La autorización de datos solo se pide al crear.
import type { ClientDetail, ClientRequest, ClientUpdateRequest } from "../api/types";

export interface ClientDraft {
  full_name: string;
  phone: string;
  document: string;
  email: string;
  notes: string;
  consent: boolean;
  other_person: boolean;
}

export type TextField = "full_name" | "phone" | "document" | "email" | "notes";

const BLANK: ClientDraft = {
  full_name: "",
  phone: "",
  document: "",
  email: "",
  notes: "",
  consent: false,
  other_person: false,
};

/** Vacío para crear; al editar, el nombre, el correo y las notas que ya tiene. */
export function initialDraft(client: ClientDetail | null): ClientDraft {
  if (client === null) return BLANK;
  return { ...BLANK, full_name: client.name, email: client.email ?? "", notes: client.notes };
}

export function toUpdate(draft: ClientDraft): ClientUpdateRequest {
  const { full_name, phone, document, email, notes } = draft;
  return { full_name, phone, document, email, notes };
}

export function toCreate(draft: ClientDraft): ClientRequest {
  return { ...toUpdate(draft), consent: draft.consent, other_person: draft.other_person };
}
