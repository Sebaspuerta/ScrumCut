// Lo que se le muestra a la persona cuando una escritura falla: los mensajes de validación del servidor
// (los mismos de las pantallas de Django) o un texto genérico. Nunca el detalle técnico del error.
import { ApiError } from "./client";

export const GENERIC_FAILURE = "No pudimos completar la acción. Intenta de nuevo.";
const GENERIC_REVIEW = "Revisa los datos enviados.";

export interface FormErrors {
  detail: string | null;
  fields: Partial<Record<string, string>>;
  code: string | null;
}

const NO_ERRORS: FormErrors = { detail: null, fields: {}, code: null };

function joinFields(fields: Record<string, string[]>): Partial<Record<string, string>> {
  return Object.fromEntries(Object.entries(fields).map(([name, messages]) => [name, messages.join(" ")]));
}

/** Los errores de una mutación para el formulario; sin error, vacío. Con errores por campo, el mensaje
 * general solo aparece si el servidor dijo algo más que «Revisa los datos enviados». */
export function formErrors(error: Error | null): FormErrors {
  if (error === null) return NO_ERRORS;
  const body = error instanceof ApiError ? error.body : null;
  if (body === null) return { ...NO_ERRORS, detail: GENERIC_FAILURE };
  const fields = joinFields(body.field_errors);
  const onlyFields = Object.keys(fields).length > 0 && body.detail === GENERIC_REVIEW;
  return { detail: onlyFields ? null : body.detail, fields, code: body.code };
}
