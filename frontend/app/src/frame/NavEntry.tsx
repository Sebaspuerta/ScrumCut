import { NavLink } from "react-router";

import type { NavItem } from "../api/types";
import { cx } from "../lib/cx";
import { Pill } from "../ui/Pill";
import { NavIcon } from "./NavIcon";
import styles from "./NavEntry.module.css";

const WITHOUT_SCREEN: Record<NavItem["status"], string> = {
  enlace: "",
  pronto: "Pronto",
  proximamente: "Próximamente",
};
const ICON_SIZE = 18;
const ICON_STROKE = 1.5;

interface NavEntryProps {
  item: NavItem;
  onNavigate: () => void;
}

/** En React, enlace del enrutador; si aún vive en Django, enlace a esa pantalla; sin pantalla, nunca enlace. */
export function NavEntry({ item, onNavigate }: NavEntryProps) {
  const icon = <NavIcon name={item.icon} size={ICON_SIZE} strokeWidth={ICON_STROKE} />;
  if (item.app_path !== null) {
    return (
      <NavLink
        to={item.app_path}
        end
        onClick={onNavigate}
        className={({ isActive }) => cx(styles.entry, isActive && styles.active)}
      >
        {icon}
        {item.label}
      </NavLink>
    );
  }
  if (item.url !== null) {
    return (
      <a className={styles.entry} href={item.url}>
        {icon}
        {item.label}
      </a>
    );
  }
  return (
    <span className={cx(styles.entry, styles.soon)}>
      {icon}
      {item.label}
      <span className={styles.tag}>
        <Pill>{WITHOUT_SCREEN[item.status]}</Pill>
      </span>
    </span>
  );
}
