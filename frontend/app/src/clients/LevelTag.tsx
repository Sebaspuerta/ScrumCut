import type { ClientLevel } from "../api/types";
import { Pill } from "../ui/Pill";
import styles from "./Clients.module.css";

const TONES: Partial<Record<ClientLevel, "positive" | "attention">> = { vip: "positive", debtor: "attention" };

interface LevelTagProps {
  level: ClientLevel | null;
  label: string;
}

/** El nivel del cliente en la sede, como lo calcula el servidor; sin nivel («Varía por sede»), solo el texto. */
export function LevelTag({ level, label }: LevelTagProps) {
  if (level === null) return <span className={styles.muted}>{label}</span>;
  return <Pill tone={TONES[level] ?? "neutral"}>{label}</Pill>;
}
