import { ArrowDown, ArrowUp } from "lucide-react";
import type { ReactNode } from "react";

import styles from "./Change.module.css";

const SPOKEN = { up: "sube", down: "baja" } as const;
const ICON_SIZE = 14;

interface ChangeProps {
  direction: "up" | "down" | null;
  children: ReactNode;
}

/** Una cifra que sube o baja: flecha de lucide con su texto para el lector de pantalla, sin rojos. */
export function Change({ direction, children }: ChangeProps) {
  if (direction === null) return <span>{children}</span>;
  const Icon = direction === "up" ? ArrowUp : ArrowDown;
  return (
    <span className={styles[direction]}>
      <Icon size={ICON_SIZE} strokeWidth={2} aria-hidden="true" />
      <span className="visually-hidden">{SPOKEN[direction]} </span>
      {children}
    </span>
  );
}
