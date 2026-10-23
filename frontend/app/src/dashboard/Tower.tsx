import type { CalendarDay } from "../api/types";
import styles from "./TowersView.module.css";

const MAX_HEIGHT = 160; // alto de la torre del mejor día
const FACES = ["north", "west", "south", "east", "top"] as const;

interface TowerProps {
  day: CalendarDay;
  onHover: (hovering: boolean) => void;
}

/** El alto va en la variable --height por el CSSOM (sin atributo style: CSP estricta). */
export function Tower({ day, onHover }: TowerProps) {
  const height = `${String(Math.round(day.ratio * MAX_HEIGHT))}px`;
  return (
    <div
      ref={(node) => {
        node?.style.setProperty("--height", height);
      }}
      className={[styles.tower, styles[`level${String(day.level)}`], day.today ? styles.today : ""].join(" ")}
      onPointerEnter={() => {
        onHover(true);
      }}
      onPointerLeave={() => {
        onHover(false);
      }}
    >
      {FACES.map((face) => (
        <div
          key={face}
          className={`${styles.face ?? ""} ${styles[face] ?? ""}`}
          data-bounds={face === "top" ? "" : undefined}
        />
      ))}
    </div>
  );
}
