import { Moon, Sun } from "lucide-react";

import type { EffectiveTheme } from "../theme/theme";
import styles from "./ThemeToggle.module.css";

interface ThemeToggleProps {
  shown: EffectiveTheme;
  onToggle: () => void;
}

/** Cambia al modo contrario del que se ve; la elección se guarda en el servidor. */
export function ThemeToggle({ shown, onToggle }: ThemeToggleProps) {
  const dark = shown === "dark";
  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={onToggle}
      aria-label={dark ? "Usar modo claro" : "Usar modo oscuro"}
    >
      {dark ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
    </button>
  );
}
