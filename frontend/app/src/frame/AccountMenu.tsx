import { useQuery } from "@tanstack/react-query";
import { LogOut, Monitor, ShieldCheck } from "lucide-react";
import { useId } from "react";

import { api } from "../api/client";
import type { Me } from "../api/types";
import { usePopover } from "../hooks/usePopover";
import { DJANGO_ROUTES } from "../lib/djangoRoutes";
import styles from "./AccountMenu.module.css";
import menu from "./Menu.module.css";

interface AccountMenuProps {
  me: Me;
  usesSystemTheme: boolean;
  onUseSystemTheme: () => void;
}

/** La cuenta: verificación en dos pasos, tema y los dos cierres de sesión, que son POST a Django. */
export function AccountMenu({ me, usesSystemTheme, onUseSystemTheme }: AccountMenuProps) {
  const menuId = useId();
  const { open, toggle, containerRef, triggerRef } = usePopover();
  const csrf = useQuery({ queryKey: ["csrf"], queryFn: () => api.csrfToken(), enabled: open });
  const role = me.role?.label ?? "";
  return (
    <div className={menu.wrapper} ref={containerRef}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.account}
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={`Cuenta de ${me.user.name}`}
        onClick={toggle}
      >
        <span className={styles.avatar} aria-hidden="true">
          {me.user.initials}
        </span>
        <b className={styles.name}>
          {me.user.name}
          <small>{role}</small>
        </b>
      </button>
      {open && (
        <div id={menuId} className={menu.menu}>
          <div className={menu.head}>
            <b>{me.user.name}</b>
            <small>
              {role} · {me.barbershop?.name} · {me.branch?.current_label}
            </small>
          </div>
          <a className={menu.item} href={DJANGO_ROUTES.security}>
            <ShieldCheck size={18} aria-hidden="true" />
            Verificación en dos pasos
          </a>
          {!usesSystemTheme && (
            <button type="button" className={menu.item} onClick={onUseSystemTheme}>
              <Monitor size={18} aria-hidden="true" />
              Usar el tema del sistema
            </button>
          )}
          <div className={menu.separator}>
            <form method="post" action={DJANGO_ROUTES.logoutEverywhere}>
              <input type="hidden" name="csrfmiddlewaretoken" value={csrf.data ?? ""} />
              <button type="submit" className={menu.item} disabled={!csrf.data}>
                Cerrar sesión en todos los dispositivos
              </button>
            </form>
            <form method="post" action={DJANGO_ROUTES.logout}>
              <input type="hidden" name="csrfmiddlewaretoken" value={csrf.data ?? ""} />
              <button type="submit" className={menu.item} disabled={!csrf.data}>
                <LogOut size={18} aria-hidden="true" />
                Cerrar sesión
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
