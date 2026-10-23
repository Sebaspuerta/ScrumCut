import { RotateCcw, RotateCw } from "lucide-react";
import { useRef, useState, type PointerEvent } from "react";

import type { CalendarWeek } from "../api/types";
import { cx } from "../lib/cx";
import { formatCop, longDate } from "../lib/format";
import { Button } from "../ui/Button";
import { paddedDays } from "./calendarWeeks";
import { Tower } from "./Tower";
import styles from "./TowersView.module.css";
import { START, useTowersRotation } from "./useTowersRotation";

const WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const TURN_STEP = 30;
const TOOLTIP_OFFSET = 14;

interface TowersViewProps {
  weeks: CalendarWeek[];
}

/** Cada torre es un día con ventas y su altura, lo vendido frente al mejor día. Hoy y la torre bajo el cursor, en el acento. */
export function TowersView({ weeks }: TowersViewProps) {
  const stageRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<HTMLDivElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);
  const [hovered, setHovered] = useState<{ label: string; amount: string } | null>(null);
  const { view, setView, drag } = useTowersRotation(stageRef, sceneRef);

  const followPointer = (event: PointerEvent<HTMLDivElement>) => {
    drag.onPointerMove(event);
    const [stage, tip] = [stageRef.current, tipRef.current];
    if (!stage || !tip) return;
    const area = stage.getBoundingClientRect();
    tip.style.left = `${String(event.clientX - area.left + TOOLTIP_OFFSET)}px`;
    tip.style.top = `${String(event.clientY - area.top + TOOLTIP_OFFSET)}px`;
  };
  const days = weeks.flatMap((week, index) => paddedDays(week, index === 0));
  return (
    <div className={styles.towers}>
      <div className={styles.controls}>
        <Button
          kind="secondary"
          aria-label="Girar a la izquierda"
          onClick={() => {
            setView({ ...view, turn: view.turn - TURN_STEP });
          }}
        >
          <RotateCcw size={16} aria-hidden="true" />
        </Button>
        <Button
          kind="secondary"
          aria-label="Girar a la derecha"
          onClick={() => {
            setView({ ...view, turn: view.turn + TURN_STEP });
          }}
        >
          <RotateCw size={16} aria-hidden="true" />
        </Button>
        <Button
          kind="secondary"
          onClick={() => {
            setView(START);
          }}
        >
          Vista inicial
        </Button>
      </div>
      <div
        ref={stageRef}
        className={styles.stage}
        role="img"
        aria-label="Torres de ventas por día: la altura de cada torre es lo vendido ese día. Arrastra para girar."
        onPointerDown={drag.onPointerDown}
        onPointerMove={followPointer}
        onPointerUp={drag.onPointerUp}
        onPointerCancel={drag.onPointerUp}
      >
        <div ref={sceneRef} className={styles.scene}>
          {days.map((day, index) => (
            <div key={day?.date ?? `vacio-${String(index)}`} className={styles.cell}>
              <div data-bounds className={cx(styles.floor, day ? day.future && styles.future : styles.outside)}>
                {day?.day}
              </div>
              {day?.has_sales && !day.future && (
                <Tower
                  day={day}
                  onHover={(on) => {
                    setHovered(on ? { label: longDate(day.date), amount: formatCop(day.total) } : null);
                  }}
                />
              )}
            </div>
          ))}
          {WEEKDAYS.map((name) => (
            <span key={name} data-bounds className={styles.axis}>
              {name}
            </span>
          ))}
        </div>
        <div ref={tipRef} className={styles.tooltip} hidden={hovered === null}>
          <span>{hovered?.label}</span>
          <strong>{hovered?.amount}</strong>
        </div>
      </div>
    </div>
  );
}
