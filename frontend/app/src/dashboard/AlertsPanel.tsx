import type { AlertItem } from "../api/types";
import { AlertRow } from "../frame/AlertRow";
import { Panel } from "../ui/Panel";
import { Pill } from "../ui/Pill";
import styles from "./AlertsPanel.module.css";

const AREA: Record<AlertItem["kind"], string> = {
  agotado: "Inventario",
  stock_bajo: "Inventario",
  por_vencer: "Inventario",
  fiado_vencido: "Cartera",
};

interface AlertsPanelProps {
  alerts: AlertItem[];
  /** null sin alertas.ver. */
  unread: number | null;
  timeZone: string;
}

/** Las alertas sin leer más recientes; la campana tiene el resto. */
export function AlertsPanel({ alerts, unread, timeZone }: AlertsPanelProps) {
  const subtitle = unread === null ? "" : unread === 1 ? "1 alerta sin leer" : `${String(unread)} alertas sin leer`;
  return (
    <Panel title="Requiere atención" subtitle={subtitle}>
      {alerts.length === 0 ? (
        <p className={styles.empty}>Nada pendiente: no hay alertas sin leer.</p>
      ) : (
        <ul className={styles.list}>
          {alerts.map((alert) => (
            <li key={alert.id} className={styles.item}>
              <AlertRow alert={alert} timeZone={timeZone} />
              <Pill>{AREA[alert.kind]}</Pill>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
