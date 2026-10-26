// Formato colombiano de la interfaz: el mismo que apps/core/formatting.py. Los casos de format-cases.json
// los prueban los dos lados (format.test.ts y tests/frontend/test_formatting.py).

const MINUS = "−"; // signo menos tipográfico, como en el backend
const EMPTY = "—";
const ROUND_UP_FROM = 5; // redondeo comercial (ROUND_HALF_UP): ,5 sube
const NOON = 12;
const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const MONTH_NAMES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];
const WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const WEEKDAY_NAMES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"];
const DECIMAL = /^(-?)(\d+)(?:\.(\d+))?$/;
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** Pesos sin decimales y con punto de miles: $1.250.000, −$8.000. Recibe el texto decimal de la API. */
export function formatCop(value: string | number | null): string {
  if (value === null) return EMPTY;
  const match = DECIMAL.exec(String(value).trim());
  if (!match) throw new RangeError(`No es un valor en pesos: ${String(value)}`);
  const [, sign, units = "0", decimals = ""] = match;
  const roundUp = Number(decimals.charAt(0) || "0") >= ROUND_UP_FROM;
  const rounded = BigInt(units) + (roundUp ? 1n : 0n);
  const digits = rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${sign && rounded > 0n ? MINUS : ""}$${digits}`;
}

interface CalendarDay {
  year: number;
  month: number; // 1 a 12
  day: number;
  weekday: number; // 0 lunes a 6 domingo
}

function calendarDay(isoDate: string): CalendarDay {
  const match = ISO_DATE.exec(isoDate);
  if (!match) throw new RangeError(`No es una fecha AAAA-MM-DD: ${isoDate}`);
  const [year, month, day] = match.slice(1).map(Number) as [number, number, number];
  const sundayFirst = new Date(Date.UTC(year, month - 1, day)).getUTCDay();
  return { year, month, day, weekday: (sundayFirst + 6) % 7 };
}

/** 0 lunes a 6 domingo. */
export function weekdayIndex(isoDate: string): number {
  return calendarDay(isoDate).weekday;
}

/** 3 oct */
export function shortDate(isoDate: string): string {
  const { month, day } = calendarDay(isoDate);
  return `${String(day)} ${MONTHS[month - 1] ?? ""}`;
}

/** Vie 9 oct */
export function dayLabel(isoDate: string): string {
  return `${WEEKDAYS[calendarDay(isoDate).weekday] ?? ""} ${shortDate(isoDate)}`;
}

/** Octubre 2026 */
export function monthLabel(isoDate: string): string {
  const { year, month } = calendarDay(isoDate);
  return `${MONTH_NAMES[month - 1] ?? ""} ${String(year)}`;
}

/** 8:00 a. m. / 3:15 p. m., en la zona horaria de la barbería. */
export function clock(isoDateTime: string, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone, hour: "numeric", minute: "2-digit", hourCycle: "h23" })
    .formatToParts(new Date(isoDateTime))
    .reduce<Record<string, string>>((found, part) => ({ ...found, [part.type]: part.value }), {});
  const hour = Number(parts.hour);
  const suffix = hour < NOON ? "a. m." : "p. m.";
  return `${String(((hour + NOON - 1) % NOON) + 1)}:${parts.minute ?? "00"} ${suffix}`;
}

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

/** Jueves, 22 de octubre (con `withYear`: Jueves, 22 de octubre de 2026). */
export function longDate(isoDate: string, withYear = false): string {
  const { year, month, day, weekday } = calendarDay(isoDate);
  const monthName = (MONTH_NAMES[month - 1] ?? "").toLowerCase();
  const text = `${WEEKDAY_NAMES[weekday] ?? ""}, ${String(day)} de ${monthName}`;
  return capitalize(withYear ? `${text} de ${String(year)}` : text);
}

/** El día (AAAA-MM-DD) de un instante en la zona horaria de la barbería. */
export function zonedDate(isoDateTime: string, timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).format(
    new Date(isoDateTime),
  );
}

/** +12,4 % o −3,1 %: sin rojos; la flecha la pone el ícono (ui/Change) junto a la cifra. */
export function formatVariation(percent: string | null): string {
  if (percent === null) return EMPTY;
  const negative = percent.trim().startsWith("-");
  const digits = percent.replace("-", "").replace(".", ",");
  return negative ? `${MINUS}${digits} %` : `+${digits} %`;
}

/** +$5.000, −$8.000 o $0: un monto que suma o resta (diferencias del arqueo, movimientos de caja). */
export function signedCop(value: string): string {
  const text = formatCop(value);
  return text.startsWith(MINUS) || text === "$0" ? text : `+${text}`;
}

/** «1 comanda», «3 comandas». */
export function countOf(count: number, one: string, many: string): string {
  return `${String(count)} ${count === 1 ? one : many}`;
}

/** −$8.000: un monto que sale de la caja (gasto, retiro, devolución); en cero, $0. */
export function outflowCop(value: string): string {
  const amount = value.trim();
  return formatCop(amount.startsWith("-") ? amount.slice(1) : `-${amount}`);
}

function previousDay(isoDate: string): string {
  const { year, month, day } = calendarDay(isoDate);
  return new Date(Date.UTC(year, month - 1, day - 1)).toISOString().slice(0, "AAAA-MM-DD".length);
}

/** Desde cuándo está abierta una caja: "desde las 8:00 a. m.", "desde ayer, 8:00 a. m." o
 * "desde el lun 19 oct, 8:00 a. m.", en la zona horaria de la barbería. */
export function openedSince(isoDateTime: string, today: string, timeZone: string): string {
  const day = zonedDate(isoDateTime, timeZone);
  const time = clock(isoDateTime, timeZone);
  if (day === today) return `desde las ${time}`;
  if (day === previousDay(today)) return `desde ayer, ${time}`;
  return `desde el ${dayLabel(day).toLowerCase()}, ${time}`;
}
