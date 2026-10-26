import { X } from "lucide-react";
import { useId, type ReactNode } from "react";

import { Dialog } from "./Dialog";
import styles from "./FormDialog.module.css";

interface FormDialogProps {
  title: string;
  subtitle?: string | undefined;
  onClose: () => void;
  children: ReactNode;
}

/** Un formulario en un panel modal (el de Administración de la referencia): Esc o la X lo cierran. */
export function FormDialog({ title, subtitle, onClose, children }: FormDialogProps) {
  const titleId = useId();
  return (
    <Dialog label={title} onClose={onClose} className={styles.box}>
      <div className={styles.head}>
        <div>
          <h2 id={titleId} className={styles.title}>
            {title}
          </h2>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
        <button type="button" className={styles.close} aria-label="Cerrar" onClick={onClose}>
          <X size={20} aria-hidden="true" />
        </button>
      </div>
      <div className={styles.body}>{children}</div>
    </Dialog>
  );
}
