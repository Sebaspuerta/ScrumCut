import { Menu, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";

import type { BranchState, Me, Navigation } from "../api/types";
import { Logo } from "../brand/Logo";
import { useHotkey } from "../hooks/useHotkey";
import { useTheme } from "../theme/useTheme";
import { Button } from "../ui/Button";
import { AccountMenu } from "./AccountMenu";
import { AdminPanel } from "./AdminPanel";
import { BranchSelector } from "./BranchSelector";
import { CommandPalette } from "./CommandPalette";
import { buildCommands, type Command } from "./commands";
import { NewMenu } from "./NewMenu";
import { NotificationsMenu } from "./NotificationsMenu";
import { ThemeToggle } from "./ThemeToggle";
import styles from "./TopBar.module.css";

interface TopBarProps {
  me: Me;
  barbershop: NonNullable<Me["barbershop"]>;
  branch: BranchState;
  /** undefined mientras llega la navegación. */
  navigation: Navigation | undefined;
  menuOpen: boolean;
  onToggleMenu: () => void;
}

export function TopBar({ me, barbershop, branch, navigation, menuOpen, onToggleMenu }: TopBarProps) {
  const theme = useTheme(me.user.theme);
  const navigate = useNavigate();
  const [palette, setPalette] = useState(false);
  const [admin, setAdmin] = useState(false);
  useHotkey({ key: "k", withCommand: true }, () => {
    setPalette((open) => !open);
  });
  const run = (command: Command) => {
    setPalette(false);
    if (command.target && "app" in command.target) void navigate(command.target.app);
    else if (command.target) window.location.assign(command.target.url);
  };

  return (
    <header className={styles.topbar}>
      <button
        type="button"
        className={styles.menuButton}
        aria-label={menuOpen ? "Cerrar el menú" : "Abrir el menú"}
        aria-expanded={menuOpen}
        aria-controls="barra-lateral"
        onClick={onToggleMenu}
      >
        <Menu size={20} aria-hidden="true" />
      </button>
      <div className={styles.logo}>
        <Logo collapsible />
      </div>
      <div className={styles.shop}>
        <small>Barbería</small>
        <b>{barbershop.name}</b>
      </div>
      <div className={styles.branch}>
        <BranchSelector branch={branch} />
      </div>
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.search}
          aria-keyshortcuts="Control+K"
          aria-label="Buscar"
          onClick={() => {
            setPalette(true);
          }}
        >
          <Search size={15} aria-hidden="true" />
          <span className={styles.searchText}>Buscar</span>
          <kbd className={styles.searchText}>Ctrl K</kbd>
        </button>
        <NewMenu actions={navigation?.new_actions ?? []} />
        <NotificationsMenu unread={navigation ? navigation.unread_alerts : null} timeZone={barbershop.timezone} />
        {navigation && navigation.administration.length > 0 && (
          <Button
            kind="secondary"
            className={styles.hideMobile}
            onClick={() => {
              setAdmin(true);
            }}
          >
            Administración
          </Button>
        )}
        <ThemeToggle shown={theme.shown} onToggle={theme.toggle} />
        <AccountMenu me={me} usesSystemTheme={theme.theme === "system"} onUseSystemTheme={theme.useSystem} />
      </div>
      {palette && navigation && (
        <CommandPalette
          commands={buildCommands(navigation)}
          onRun={run}
          onClose={() => {
            setPalette(false);
          }}
        />
      )}
      {admin && navigation && (
        <AdminPanel
          groups={navigation.administration}
          summary={navigation.administration_summary}
          timeZone={barbershop.timezone}
          onClose={() => {
            setAdmin(false);
          }}
        />
      )}
    </header>
  );
}
