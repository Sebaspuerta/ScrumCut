import { Link } from "react-router";

import styles from "./TabLinks.module.css";

export interface TabLink {
  value: string;
  label: string;
  count: number;
}

interface TabLinksProps {
  tabs: TabLink[];
  current: string;
  label: string;
  /** La búsqueda de la URL al elegir cada pestaña: el estado va en la URL. */
  searchFor: (value: string) => string;
}

/** Pestañas con su conteo (Abiertas, Pendientes…): enlaces con aria-current. */
export function TabLinks({ tabs, current, label, searchFor }: TabLinksProps) {
  return (
    <nav className={styles.tabs} aria-label={label}>
      {tabs.map((tab) => (
        <Link
          key={tab.value}
          className={styles.tab}
          to={{ search: searchFor(tab.value) }}
          aria-current={tab.value === current ? "page" : undefined}
        >
          {tab.label} <b className={styles.count}>{tab.count}</b>
        </Link>
      ))}
    </nav>
  );
}
