import { ChevronLeft, ChevronRight } from "lucide-react";
import { Link, useSearchParams } from "react-router";

import type { Dashboard } from "../api/types";
import { Panel } from "../ui/Panel";
import { SalesCalendar } from "./SalesCalendar";
import styles from "./SalesPanel.module.css";
import { TowersView } from "./TowersView";

interface SalesPanelProps {
  data: Dashboard;
  view: "calendar" | "3d";
}

/** Los enlaces conservan el resto de la URL: el mes y la vista son estado de la página, no del navegador. */
function useLinkWith() {
  const [params] = useSearchParams();
  return (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null) next.delete(key);
      else next.set(key, value);
    }
    return `?${next.toString()}`;
  };
}

export function SalesPanel({ data, view }: SalesPanelProps) {
  const linkWith = useLinkWith();
  const monthNav = (
    <nav className={styles.monthNav} aria-label="Cambiar de mes">
      {data.previous_month ? (
        <Link className={styles.arrow} to={linkWith({ mes: data.previous_month })} aria-label="Mes anterior">
          <ChevronLeft size={16} aria-hidden="true" />
        </Link>
      ) : (
        <span className={styles.arrowOff} aria-hidden="true">
          <ChevronLeft size={16} />
        </span>
      )}
      <p className={styles.month}>{data.month_label}</p>
      {data.next_month ? (
        <Link className={styles.arrow} to={linkWith({ mes: data.next_month })} aria-label="Mes siguiente">
          <ChevronRight size={16} aria-hidden="true" />
        </Link>
      ) : (
        <span className={styles.arrowOff} aria-hidden="true">
          <ChevronRight size={16} />
        </span>
      )}
    </nav>
  );
  const switcher = (
    <div className={styles.seg} aria-label="Vista de las ventas" role="group">
      <Link to={linkWith({ vista: null })} aria-current={view === "calendar"}>
        Calendario
      </Link>
      <Link to={linkWith({ vista: "3d" })} aria-current={view === "3d"}>
        Torres 3D
      </Link>
    </div>
  );
  return (
    <Panel title="Ventas por día" subtitle={monthNav} actions={switcher} className={styles.panel}>
      {view === "3d" ? <TowersView weeks={data.calendar.weeks} /> : <SalesCalendar calendar={data.calendar} />}
    </Panel>
  );
}
