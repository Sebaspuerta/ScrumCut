import { useId } from "react";

import type { NavGroup } from "../api/types";
import { NavEntry } from "./NavEntry";
import styles from "./NavGroupSection.module.css";

interface NavGroupSectionProps {
  group: NavGroup;
  onNavigate: () => void;
}

export function NavGroupSection({ group, onNavigate }: NavGroupSectionProps) {
  const titleId = useId();
  return (
    <section className={styles.group} aria-labelledby={titleId}>
      <h2 id={titleId} className={styles.title}>
        {group.title}
      </h2>
      <ul className={styles.items}>
        {group.items.map((item) => (
          <li key={item.label}>
            <NavEntry item={item} onNavigate={onNavigate} />
          </li>
        ))}
      </ul>
    </section>
  );
}
