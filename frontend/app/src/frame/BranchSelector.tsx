import { Check, ChevronDown } from "lucide-react";
import { useId } from "react";

import type { BranchState } from "../api/types";
import { usePopover } from "../hooks/usePopover";
import { useSwitchBranch } from "../hooks/useSwitchBranch";
import styles from "./BranchSelector.module.css";

const ALL_BRANCHES: BranchState["mode"] = "todas";

interface BranchSelectorProps {
  branch: BranchState;
}

/** La sede activa. Las opciones, "Todas las sedes" y "Gestionar sedes" las decide el servidor. */
export function BranchSelector({ branch }: BranchSelectorProps) {
  const menuId = useId();
  const { open, close, toggle, containerRef, triggerRef } = usePopover();
  const switchBranch = useSwitchBranch();
  const isAll = branch.mode === ALL_BRANCHES;

  if (branch.options.length <= 1 && !branch.can_view_all) {
    return <p className={styles.fixed}>Sede: {branch.current_label}</p>;
  }
  const choose = (token: string) => {
    close();
    switchBranch.mutate(token);
  };
  return (
    <div className={styles.wrapper} ref={containerRef}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.selector}
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={`Sede: ${branch.current_label}. Cambiar de sede`}
        disabled={switchBranch.isPending}
        onClick={toggle}
      >
        {branch.current_label}
        {isAll && <span className={styles.note}>· vista consolidada</span>}
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      {open && (
        <ul id={menuId} className={styles.menu} aria-label="Sedes">
          {branch.can_view_all && (
            <li>
              <button
                type="button"
                className={styles.option}
                aria-current={isAll}
                onClick={() => {
                  choose(ALL_BRANCHES);
                }}
              >
                Todas las sedes <span className={styles.note}>· vista consolidada</span>
                {isAll && <Check size={16} aria-hidden="true" className={styles.check} />}
              </button>
            </li>
          )}
          {branch.options.map((option) => (
            <li key={option.token}>
              <button
                type="button"
                className={styles.option}
                aria-current={option.current}
                onClick={() => {
                  choose(option.token);
                }}
              >
                {option.label}
                {option.current && <Check size={16} aria-hidden="true" className={styles.check} />}
              </button>
            </li>
          ))}
          {branch.can_manage && (
            <li className={styles.manage}>
              <span>Gestionar sedes</span>
              <span className={styles.note}>Próximamente</span>
            </li>
          )}
        </ul>
      )}
      {switchBranch.isError && (
        <p role="alert" className={styles.error}>
          No pudimos cambiar de sede. Intenta de nuevo.
        </p>
      )}
    </div>
  );
}
