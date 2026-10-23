import styles from "./Sparkline.module.css";

const WIDTH = 80;
const HEIGHT = 22;
const PADDING = 3;

/** Los puntos de la línea dentro de 80 × 22, el valor más alto arriba. */
export function sparkPoints(values: number[]): string {
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const step = (WIDTH - 2 * PADDING) / Math.max(values.length - 1, 1);
  return values
    .map((value, index) => {
      const x = PADDING + index * step;
      const y = HEIGHT - PADDING - ((value - min) / span) * (HEIGHT - 2 * PADDING);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

/** Mini tendencia decorativa: la cifra y su nota ya dicen lo importante en texto. */
export function Sparkline({ values }: { values: number[] }) {
  return (
    <svg className={styles.trend} viewBox={`0 0 ${String(WIDTH)} ${String(HEIGHT)}`} aria-hidden="true">
      <polyline points={sparkPoints(values)} />
    </svg>
  );
}
