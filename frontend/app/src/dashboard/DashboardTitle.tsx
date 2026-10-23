import { Download, RefreshCw } from "lucide-react";

import type { Dashboard } from "../api/types";
import { cx } from "../lib/cx";
import { DJANGO_ROUTES } from "../lib/djangoRoutes";
import { clock, longDate } from "../lib/format";
import { buttonClass } from "../ui/Button";
import styles from "./DashboardTitle.module.css";

interface DashboardTitleProps {
  data: Dashboard;
  updatedAt: number;
  refreshing: boolean;
  canExport: boolean;
  onRefresh: () => void;
}

/** Encabezado: fecha y alcance, cuándo se actualizó, refrescar y exportar (solo con reportes.exportar). */
export function DashboardTitle({ data, updatedAt, refreshing, canExport, onRefresh }: DashboardTitleProps) {
  const exportUrl = `${DJANGO_ROUTES.export}?${new URLSearchParams({ mes: data.month }).toString()}`;
  return (
    <div className={styles.row}>
      <div>
        <p className={styles.eyebrow}>Tablero</p>
        <h1 className={styles.title}>Resumen ejecutivo</h1>
        <p className={styles.subtitle}>
          {longDate(data.today, true)} · {data.scope_label}
        </p>
      </div>
      <div className={styles.tools}>
        <span className={styles.updated}>
          Actualizado a las {clock(new Date(updatedAt).toISOString(), data.timezone)}
        </span>
        <button
          type="button"
          className={styles.refresh}
          aria-label="Refrescar"
          onClick={onRefresh}
          disabled={refreshing}
        >
          <RefreshCw size={16} aria-hidden="true" />
        </button>
        {canExport && (
          <a className={cx(buttonClass("secondary"), styles.export)} href={exportUrl}>
            <Download size={16} aria-hidden="true" />
            Exportar informe
          </a>
        )}
      </div>
    </div>
  );
}
