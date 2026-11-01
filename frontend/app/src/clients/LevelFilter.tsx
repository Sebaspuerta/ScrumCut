import type { ClientList } from "../api/types";
import styles from "./Clients.module.css";

interface LevelFilterProps {
  levels: ClientList["levels"];
  current: string;
  onPick: (level: string) => void;
}

/** Todos, Nuevo, Frecuente, VIP, Inactivo y Deudor con su conteo: botones con aria-pressed; el nivel va en la URL. */
export function LevelFilter({ levels, current, onPick }: LevelFilterProps) {
  return (
    <div className={styles.levels} role="group" aria-label="Filtrar por nivel">
      {levels.map((level) => (
        <button
          key={level.value}
          type="button"
          className={styles.level}
          aria-pressed={level.value === current}
          onClick={() => {
            onPick(level.value);
          }}
        >
          {level.label} <b className={styles.count}>{level.count}</b>
        </button>
      ))}
    </div>
  );
}
