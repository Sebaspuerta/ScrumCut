import type { ClientActivity } from "../api/types";
import { cssVar } from "../lib/cssVar";
import { countOf } from "../lib/format";
import styles from "./Clients.module.css";

interface ClientLevelProps {
  activity: ClientActivity;
  branch: string;
}

function progressNote(activity: ClientActivity): string {
  const visits = countOf(activity.visits, "visita", "visitas");
  const { next, missing } = activity.progress;
  return next === null
    ? `${visits} · el nivel más alto por visitas`
    : `${visits} · ${String(missing)} más para ${next}`;
}

/** El nivel en la sede con su barra al siguiente (Nuevo → Frecuente → VIP), con los umbrales de la barbería. */
export function ClientLevel({ activity, branch }: ClientLevelProps) {
  const percent = activity.progress.percent;
  return (
    <div>
      <p className={styles.eyebrow}>Nivel en {branch}</p>
      <h3>{activity.level_label}</h3>
      <div
        className={styles.progress}
        role="progressbar"
        aria-label="Avance al siguiente nivel"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <i ref={cssVar("--progress", `${String(percent)}%`)} />
      </div>
      <p className={styles.muted}>{progressNote(activity)}</p>
    </div>
  );
}
