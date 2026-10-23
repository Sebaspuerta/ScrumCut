import type { ReactNode } from "react";

import styles from "./Pill.module.css";

interface PillProps {
  tone?: "neutral" | "positive" | "attention";
  children: ReactNode;
}

export function Pill({ tone = "neutral", children }: PillProps) {
  return <span className={[styles.pill, tone === "neutral" ? "" : styles[tone]].join(" ")}>{children}</span>;
}
