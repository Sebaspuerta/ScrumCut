import { Fragment } from "react";

import type { Dashboard } from "../api/types";
import { formatCop } from "../lib/format";
import { CalendarCell } from "./CalendarCell";
import { paddedDays } from "./calendarWeeks";
import styles from "./SalesCalendar.module.css";

const WEEK_HEAD = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom", "Semana"];
const LEGEND_LEVELS = [1, 2, 3, 4, 5] as const;

interface SalesCalendarProps {
  calendar: Dashboard["calendar"];
}

/** El mes de lunes a domingo, con el total de cada semana. Más oscuro, más vendido frente al mejor día. */
export function SalesCalendar({ calendar }: SalesCalendarProps) {
  return (
    <>
      <div className={styles.scroller}>
        <div className={styles.weekHead} aria-hidden="true">
          {WEEK_HEAD.map((name) => (
            <b key={name}>{name}</b>
          ))}
        </div>
        <ol className={styles.calendar} aria-label="Ventas por día del mes">
          {calendar.weeks.map((week, row) => (
            <Fragment key={week.days[0]?.date ?? row}>
              {paddedDays(week, row === 0).map((day, column) => (
                <CalendarCell key={day?.date ?? `vacio-${String(row)}-${String(column)}`} day={day} />
              ))}
              <li className={styles.weekTotal}>
                <span>Total</span>
                <b>{formatCop(week.total)}</b>
              </li>
            </Fragment>
          ))}
        </ol>
      </div>
      <div className={styles.legend} aria-hidden="true">
        <span>Menor venta</span>
        {LEGEND_LEVELS.map((level) => (
          <i key={level} className={styles[`h${String(level)}`]} />
        ))}
        <span>Mayor venta</span>
      </div>
    </>
  );
}
