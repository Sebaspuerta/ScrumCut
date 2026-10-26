import { Link } from "react-router";

import type { Dashboard } from "../api/types";
import { CASH_PATH } from "../lib/appRoutes";
import { clock, formatCop } from "../lib/format";
import { cx } from "../lib/cx";
import { buttonClass } from "../ui/Button";
import { Panel } from "../ui/Panel";
import { Pill } from "../ui/Pill";
import styles from "./CashPanel.module.css";

interface CashPanelProps {
  cash: Dashboard["cash"];
  canOpenCash: boolean;
  timeZone: string;
}

const SIGNS: Record<string, string> = { up: "+ ", down: "− ", total: "", counted: "" };

/** Cuadre de hoy, de la apertura al esperado. En "todas" no se mezclan cajas: pide elegir una sede. */
export function CashPanel({ cash, canOpenCash, timeZone }: CashPanelProps) {
  const flow = cash.flow;
  const status = flow ? (
    <Pill tone={flow.is_open ? "positive" : "neutral"}>{flow.is_open ? "Abierta" : "Cerrada"}</Pill>
  ) : null;
  const subtitle = flow ? `Desde las ${clock(flow.opened_at, timeZone)}` : "Hoy";
  return (
    <Panel title="Cuadre de caja" subtitle={subtitle} actions={status} className={styles.cash}>
      {cash.needs_branch && <p className={styles.empty}>Elige una sede para ver su caja.</p>}
      {!cash.needs_branch && !flow && <p className={styles.empty}>Hoy no se ha abierto la caja de esta sede.</p>}
      {flow && (
        <dl className={styles.rows}>
          {flow.steps
            .filter((step) => step.kind !== "counted" && step.label !== "Esperado")
            .map((step) => (
              <div key={step.label} className={styles.row}>
                <dt>
                  {SIGNS[step.kind]}
                  {step.label}
                </dt>
                <dd>{step.kind === "down" ? formatCop(`-${step.amount}`) : formatCop(step.amount)}</dd>
              </div>
            ))}
          <div className={cx(styles.row, styles.total)}>
            <dt>Esperado</dt>
            <dd>{formatCop(flow.expected)}</dd>
          </div>
          <div className={styles.row}>
            <dt>Contado</dt>
            <dd>
              {flow.is_open ? "—" : formatCop(flow.steps.find((step) => step.kind === "counted")?.amount ?? null)}
            </dd>
          </div>
        </dl>
      )}
      {canOpenCash && !cash.needs_branch && (
        <Link className={cx(buttonClass("secondary", true), styles.go)} to={CASH_PATH}>
          Ir a caja
        </Link>
      )}
    </Panel>
  );
}
