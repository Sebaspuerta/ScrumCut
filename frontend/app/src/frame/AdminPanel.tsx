import { ChevronRight, X } from "lucide-react";

import type { AdministrationSummary, NavGroup } from "../api/types";
import { clock, shortDate, zonedDate } from "../lib/format";
import { Dialog } from "../ui/Dialog";
import styles from "./AdminPanel.module.css";

interface AdminPanelProps {
  groups: NavGroup[];
  summary: AdministrationSummary | null;
  timeZone: string;
  onClose: () => void;
}

/** Los grupos de Administración que da la API; lo que aún no tiene pantalla sale apagado y nunca es enlace. */
export function AdminPanel({ groups, summary, timeZone, onClose }: AdminPanelProps) {
  const change = summary?.last_change;
  return (
    <Dialog label="Administración" onClose={onClose} className={styles.admin}>
      <div className={styles.top}>
        <h2>Administración</h2>
        <button type="button" className={styles.close} aria-label="Cerrar" onClick={onClose}>
          <X size={20} aria-hidden="true" />
        </button>
      </div>
      <div className={styles.body}>
        <div className={styles.groups}>
          {groups.map((group) => (
            <section key={group.title} aria-label={group.title}>
              <h3 className={styles.groupTitle}>{group.title}</h3>
              <ul className={styles.items}>
                {group.items.map((item) => (
                  <li key={item.label} className={item.url ? "" : styles.soon}>
                    {item.url ? <a href={item.url}>{item.label}</a> : <span>{item.label}</span>}
                    {item.url ? <ChevronRight size={14} aria-hidden="true" /> : <small>Próximamente</small>}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
        {summary && (
          <aside className={styles.aside} aria-label="Estado de la cuenta">
            <p className={styles.eyebrow}>Estado de la cuenta</p>
            <dl className={styles.facts}>
              {summary.branches && (
                <div>
                  <dt>Sedes activas</dt>
                  <dd>
                    {summary.branches.active} de {summary.branches.limit}
                  </dd>
                </div>
              )}
              {summary.members !== null && (
                <div>
                  <dt>Usuarios activos</dt>
                  <dd>{summary.members}</dd>
                </div>
              )}
            </dl>
            {summary.can_see_audit && (
              <>
                <p className={styles.eyebrow}>Último cambio</p>
                {change ? (
                  <p>
                    {change.actor}: {change.action}
                    <small>
                      {shortDate(zonedDate(change.at, timeZone))}, {clock(change.at, timeZone)}
                    </small>
                  </p>
                ) : (
                  <p>Todavía no hay cambios registrados.</p>
                )}
              </>
            )}
          </aside>
        )}
      </div>
    </Dialog>
  );
}
