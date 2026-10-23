import type { CalendarDay, CalendarWeek } from "../api/types";
import { weekdayIndex } from "../lib/format";

const DAYS_IN_WEEK = 7;

/** Los siete lugares de la semana: casillas vacías antes del día 1 y después del último día del mes. */
export function paddedDays(week: CalendarWeek, isFirstWeek: boolean): (CalendarDay | null)[] {
  const first = week.days[0];
  const lead = isFirstWeek && first ? weekdayIndex(first.date) : 0;
  const cells: (CalendarDay | null)[] = [...Array<null>(lead).fill(null), ...week.days];
  return [...cells, ...Array<null>(Math.max(DAYS_IN_WEEK - cells.length, 0)).fill(null)];
}
