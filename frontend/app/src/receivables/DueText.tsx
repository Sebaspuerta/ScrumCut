import type { ReceivableRow } from "../api/types";
import styles from "./Receivables.module.css";

const TONES: Partial<Record<string, string>> = {
  overdue: styles.overdue,
  soon: styles.soon,
  ok: styles.ok,
  done: styles.done,
};

interface DueTextProps {
  receivable: Pick<ReceivableRow, "due_text" | "due_tone">;
}

/** «▾ Vencido hace 3 días», «Vence en 2 días» o «Al día», como lo escribe el servidor: sin rojos. */
export function DueText({ receivable }: DueTextProps) {
  return <span className={TONES[receivable.due_tone]}>{receivable.due_text}</span>;
}
