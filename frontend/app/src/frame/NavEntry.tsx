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

/** Con pantalla, enlace del enrutador; sin pantalla, nunca enlace. */
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
  return (
    <span className={cx(styles.entry, styles.soon)}>
      {icon}
      <span className={styles.label}>{item.label}</span>
      <span className={styles.tag}>
        <Pill>{WITHOUT_SCREEN[item.status]}</Pill>
      </span>
    </span>
  );
}
