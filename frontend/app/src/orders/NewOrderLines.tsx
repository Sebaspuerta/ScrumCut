import { Plus, X } from "lucide-react";
import { useState } from "react";

import type { OrderCatalog } from "../api/types";
import { Button } from "../ui/Button";
import { FormAlert } from "../ui/FormAlert";
import { EMPTY_LINE, itemName, type LineDraft } from "./lineDraft";
import { LineInputs } from "./LineInputs";
import styles from "./OrderDetail.module.css";

interface NewOrderLinesProps {
  catalog: OrderCatalog;
  lines: LineDraft[];
  error: string | undefined;
  onChange: (lines: LineDraft[]) => void;
}

/** Las líneas con que se abre la comanda: se eligen una a una y se pueden quitar antes de abrirla. */
export function NewOrderLines({ catalog, lines, error, onChange }: NewOrderLinesProps) {
  const [draft, setDraft] = useState(EMPTY_LINE);
  return (
    <div className={styles.dialogBody}>
      <h3 className={styles.subhead}>Servicios y productos</h3>
      <LineInputs catalog={catalog} draft={draft} errors={{}} defaultBarber="El de la comanda" onChange={setDraft} />
      <Button
        kind="secondary"
        disabled={draft.item === ""}
        onClick={() => {
          onChange([...lines, draft]);
          setDraft(EMPTY_LINE);
        }}
      >
        <Plus size={16} aria-hidden="true" />
        Agregar a la comanda
      </Button>
      {lines.length > 0 && (
        <ul className={styles.lines} aria-label="Líneas para abrir la comanda">
          {lines.map((line, index) => (
            <li key={`${line.item}-${String(index)}`} className={styles.line}>
              <span className={styles.lineText}>
                <b>{itemName(catalog, line.item)}</b>
                <small>× {line.quantity}</small>
              </span>
              <button
                type="button"
                className={styles.remove}
                aria-label={`Quitar ${itemName(catalog, line.item)}`}
                onClick={() => {
                  onChange(lines.filter((_, at) => at !== index));
                }}
              >
                <X size={16} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <FormAlert message={error ?? null} />
    </div>
  );
}
