import type { UseQueryResult } from "@tanstack/react-query";
import { ChevronRight, Sparkles } from "lucide-react";
import type { ReactNode } from "react";

import type { BranchState, Navigation } from "../api/types";
import { Logo } from "../brand/Logo";
import { useEscape } from "../hooks/useEscape";
import { BranchSelector } from "./BranchSelector";
import { NavGroupSection } from "./NavGroupSection";
import styles from "./Sidebar.module.css";
import { StatusMessage } from "./StatusMessage";

interface SidebarProps {
  navigation: UseQueryResult<Navigation>;
  branch: BranchState;
  /** En el celular la barra es un panel que se abre desde la barra superior. */
  open: boolean;
  onClose: () => void;
  onOpenAssistant: () => void;
}

function content(navigation: UseQueryResult<Navigation>, onClose: () => void): ReactNode {
  if (navigation.isPending) return <StatusMessage kind="loading">Cargando el menú…</StatusMessage>;
  if (navigation.isError) {
    return (
      <StatusMessage kind="error" onRetry={() => void navigation.refetch()}>
        No pudimos cargar el menú.
      </StatusMessage>
    );
  }
  if (navigation.data.sidebar.length === 0)
    return <StatusMessage kind="empty">No hay secciones para tu rol.</StatusMessage>;
  return navigation.data.sidebar.map((group) => (
    <NavGroupSection key={group.title} group={group} onNavigate={onClose} />
  ));
}

/** Grupos e ítems de la API, ya filtrados por el permiso del rol en el servidor. */
export function Sidebar({ navigation, branch, open, onClose, onOpenAssistant }: SidebarProps) {
  useEscape(open, onClose);
  return (
    <>
      {open && <div className={styles.scrim} onMouseDown={onClose} aria-hidden="true" />}
      <aside id="barra-lateral" className={[styles.sidebar, open ? styles.open : ""].join(" ")}>
        {open && (
          <div className={styles.mobileHead}>
            <Logo />
            <BranchSelector branch={branch} />
          </div>
        )}
        <nav className={styles.nav} aria-label="Navegación principal">
          {content(navigation, onClose)}
        </nav>
        <div className={styles.foot}>
          <button type="button" className={styles.assistant} onClick={onOpenAssistant}>
            <Sparkles size={18} strokeWidth={1.5} aria-hidden="true" />
            <b>Asistente</b>
            <ChevronRight size={16} aria-hidden="true" className={styles.chevron} />
          </button>
          <small className={styles.signature}>ScrumCut · por ScrumTech Solutions</small>
        </div>
      </aside>
    </>
  );
}
