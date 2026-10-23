import { Bell, X } from "lucide-react";
import { useId } from "react";

import { usePopover } from "../hooks/usePopover";
import { useNotifications } from "../hooks/useNotifications";
import { AlertRow } from "./AlertRow";
import styles from "./NotificationsMenu.module.css";
import { StatusMessage } from "./StatusMessage";

interface NotificationsMenuProps {
  /** null sin alertas.ver: no hay campana. */
  unread: number | null;
  timeZone: string;
}

/** La campana: el panel trae las alertas reales del alcance al abrirse, en Hoy y Anteriores. */
export function NotificationsMenu({ unread, timeZone }: NotificationsMenuProps) {
  const panelId = useId();
  const titleId = useId();
  const { open, close, toggle, containerRef, triggerRef } = usePopover();
  const notifications = useNotifications(open);
  if (unread === null) return null;
  const label = unread ? `Notificaciones: ${String(unread)} sin leer` : "Notificaciones";
  return (
    <div ref={containerRef}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.bell}
        aria-label={label}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={toggle}
      >
        <Bell size={19} aria-hidden="true" />
        {unread > 0 && <i className={styles.count}>{unread}</i>}
      </button>
      {open && (
        <section id={panelId} className={styles.panel} aria-labelledby={titleId}>
          <div className={styles.head}>
            <div>
              <h2 id={titleId}>Notificaciones</h2>
              <p>{unread === 1 ? "1 pendiente" : `${String(unread)} pendientes`}</p>
            </div>
            <button type="button" className={styles.close} aria-label="Cerrar" onClick={close}>
              <X size={18} aria-hidden="true" />
            </button>
          </div>
          {notifications.isPending && <StatusMessage kind="loading">Cargando alertas…</StatusMessage>}
          {notifications.isError && <StatusMessage kind="error">No pudimos cargar las alertas.</StatusMessage>}
          {notifications.data?.groups.length === 0 && (
            <StatusMessage kind="empty">Todo al día: no hay alertas.</StatusMessage>
          )}
          {notifications.data?.groups.map((group) => (
            <div key={group.title} className={styles.group}>
              <h3 className={styles.groupTitle}>{group.title}</h3>
              <ul className={styles.items}>
                {group.items.map((alert) => (
                  <li key={alert.id}>
                    <AlertRow alert={alert} timeZone={timeZone} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
