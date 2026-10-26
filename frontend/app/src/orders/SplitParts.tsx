import { Plus, X } from "lucide-react";

import { cx } from "../lib/cx";
import { formatCop } from "../lib/format";
import { fromCents, digitsOnly } from "../lib/money";
import { Button } from "../ui/Button";
import input from "../ui/Input.module.css";
import { emptyPart, remainingCents, type CheckoutDraft, type PartDraft } from "./checkoutDraft";
import type { MethodOption } from "./PayMethods";
import { ReferenceInput } from "./ReferenceInput";
import styles from "./SplitParts.module.css";

interface SplitPartsProps {
  draft: CheckoutDraft;
  methods: MethodOption[];
  /** Las partes que acepta el servidor (catálogo de la sede). */
  maxParts: number;
  total: string;
  error: string | undefined;
  onChange: (draft: CheckoutDraft) => void;
}

function remainingText(cents: number): string {
  if (cents === 0) return "Asignado todo el total.";
  if (cents > 0) return `Falta por asignar ${formatCop(fromCents(cents))}.`;
  return `Te pasaste del total por ${formatCop(fromCents(-cents))}.`;
}

/** Hasta 3 partes de forma y monto; muestra lo que falta por asignar y no deja cobrar si no cuadra. */
export function SplitParts({ draft, methods, maxParts, total, error, onChange }: SplitPartsProps) {
  const setPart = (index: number, part: PartDraft) => {
    onChange({ ...draft, parts: draft.parts.map((current, at) => (at === index ? part : current)) });
  };
  const remaining = remainingCents(draft, total) ?? 0;
  return (
    <fieldset className={styles.split}>
      <legend className={styles.legend}>Pago dividido · las partes deben sumar {formatCop(total)}</legend>
      {draft.parts.map((part, index) => {
        const number = String(index + 1);
        return (
          <div key={number} className={styles.part}>
            <select
              className={input.input}
              aria-label={`Forma de pago de la parte ${number}`}
              value={part.method}
              onChange={(event) => {
                setPart(index, { ...part, method: event.target.value });
              }}
            >
              <option value="">Forma de pago</option>
              {methods.map((method) => (
                <option key={method.value} value={method.value}>
                  {method.label}
                </option>
              ))}
            </select>
            <input
              className={cx(input.input, input.figure)}
              aria-label={`Monto de la parte ${number}`}
              inputMode="numeric"
              placeholder="Monto"
              value={part.amount}
              onChange={(event) => {
                setPart(index, { ...part, amount: digitsOnly(event.target.value) });
              }}
            />
            <ReferenceInput
              aria-label={`Referencia de la parte ${number}`}
              value={part.reference}
              onChange={(reference) => {
                setPart(index, { ...part, reference });
              }}
            />
            <button
              type="button"
              className={styles.remove}
              aria-label={`Quitar la parte ${number}`}
              disabled={draft.parts.length <= 1}
              onClick={() => {
                onChange({ ...draft, parts: draft.parts.filter((_, at) => at !== index) });
              }}
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        );
      })}
      {draft.parts.length < maxParts && (
        <Button
          kind="text"
          onClick={() => {
            onChange({ ...draft, parts: [...draft.parts, emptyPart("")] });
          }}
        >
          <Plus size={16} aria-hidden="true" />
          Agregar parte
        </Button>
      )}
      <p className={remaining === 0 ? styles.balanced : styles.remaining} aria-live="polite">
        {remainingText(remaining)}
      </p>
      {error && <p className={styles.error}>{error}</p>}
    </fieldset>
  );
}
