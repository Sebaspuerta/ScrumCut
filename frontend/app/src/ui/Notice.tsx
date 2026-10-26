import type { ReactNode } from "react";

import styles from "./Notice.module.css";

interface NoticeProps {
  children: ReactNode;
  action?: ReactNode;
}

/** Un aviso de la referencia (borde y fondo de atención, sin rojos), con su acción a la derecha. */
export function Notice({ children, action }: NoticeProps) {
  return (
    <div className={styles.notice} role="status">
      <span>{children}</span>
      {action}
    </div>
  );
}
