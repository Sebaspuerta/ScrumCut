import { useId, type ReactNode } from "react";

import styles from "./Panel.module.css";

interface PanelProps {
  title: string;
  /** Texto bajo el título o un bloque propio (por ejemplo, el cambio de mes). */
  subtitle?: ReactNode;
  actions?: ReactNode;
  className?: string | undefined;
  children: ReactNode;
}

/** Un panel del tablero: título en Libre Baskerville, descripción y acciones a la derecha. */
export function Panel({ title, subtitle, actions, className = "", children }: PanelProps) {
  const titleId = useId();
  return (
    <section className={[styles.panel, className].join(" ")} aria-labelledby={titleId}>
      <div className={styles.head}>
        <div>
          <h2 id={titleId} className={styles.title}>
            {title}
          </h2>
          {typeof subtitle === "string" ? <p className={styles.subtitle}>{subtitle}</p> : subtitle}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}
