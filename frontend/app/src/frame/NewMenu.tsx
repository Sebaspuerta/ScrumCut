import { Plus } from "lucide-react";
import { useId } from "react";
import { Link } from "react-router";

import type { NavItem } from "../api/types";
import { useHotkey } from "../hooks/useHotkey";
import { usePopover } from "../hooks/usePopover";
import { cx } from "../lib/cx";
import { buttonClass } from "../ui/Button";
import styles from "./Menu.module.css";
import { NavIcon } from "./NavIcon";

interface NewMenuProps {
  actions: NavItem[];
}

/** "+ Nuevo" (atajo N): las acciones que ya tienen pantalla y que el rol puede usar. */
export function NewMenu({ actions }: NewMenuProps) {
  const menuId = useId();
  const { open, toggle, close, containerRef, triggerRef } = usePopover();
  useHotkey({ key: "n" }, toggle);
  const ready = actions.flatMap(({ label, icon, app_path }) => (app_path ? [{ label, icon, path: app_path }] : []));
  if (ready.length === 0) return null;
  return (
    <div className={styles.wrapper} ref={containerRef}>
      <button
        ref={triggerRef}
        type="button"
        className={cx(buttonClass("primary"), styles.hideMobile)}
        aria-expanded={open}
        aria-controls={menuId}
        aria-keyshortcuts="N"
        onClick={toggle}
      >
        <Plus size={16} aria-hidden="true" />
        Nuevo <kbd>N</kbd>
      </button>
      {open && (
        <ul id={menuId} className={styles.menu} aria-label="Crear">
          {ready.map(({ label, icon, path }) => (
            <li key={label}>
              <Link className={styles.item} to={path} onClick={close}>
                <NavIcon name={icon} size={18} />
                {label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
