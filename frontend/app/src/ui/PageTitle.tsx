import type { ReactNode } from "react";

import styles from "./PageTitle.module.css";

interface PageTitleProps {
  eyebrow: string;
  title: string;
  subtitle: ReactNode;
  actions?: ReactNode;
}

/** El encabezado de una pantalla (title-row de la referencia): rótulo, título, descripción y acciones. */
export function PageTitle({ eyebrow, title, subtitle, actions }: PageTitleProps) {
  return (
    <div className={styles.row}>
      <div>
        <p className={styles.eyebrow}>{eyebrow}</p>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.subtitle}>{subtitle}</p>
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </div>
  );
}
