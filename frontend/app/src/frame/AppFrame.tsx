import { useState } from "react";
import { Outlet, useLocation } from "react-router";

import { useMe } from "../hooks/useMe";
import { useNavigation } from "../hooks/useNavigation";
import styles from "./AppFrame.module.css";
import { AccessPage } from "./AccessPage";
import { AssistantPanel } from "./AssistantPanel";
import { ScreenErrorBoundary } from "./ScreenErrorBoundary";
import { Sidebar } from "./Sidebar";
import { LoadError } from "./LoadError";
import { StatusMessage } from "./StatusMessage";
import { TopBar } from "./TopBar";

/** El marco de la app: barra superior y barra lateral, armadas solo con lo que entregan me y navigation. */
export function AppFrame() {
  const me = useMe();
  const navigation = useNavigation(me.data?.barbershop != null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [assistant, setAssistant] = useState(false);
  const { pathname } = useLocation();

  if (me.isPending) return <StatusMessage kind="loading">Cargando tu cuenta…</StatusMessage>;
  if (me.isError) {
    return (
      <LoadError error={me.error} onRetry={() => void me.refetch()}>
        No pudimos cargar tu cuenta.
      </LoadError>
    );
  }
  const { barbershop, branch } = me.data;
  if (barbershop === null || branch === null) return <AccessPage access={me.data.access} />;
  return (
    <div className={styles.app}>
      <a className={styles.skip} href="#contenido">
        Saltar al contenido
      </a>
      <TopBar
        me={me.data}
        barbershop={barbershop}
        branch={branch}
        navigation={navigation.data}
        menuOpen={menuOpen}
        onToggleMenu={() => {
          setMenuOpen((open) => !open);
        }}
      />
      <Sidebar
        navigation={navigation}
        branch={branch}
        open={menuOpen}
        onClose={() => {
          setMenuOpen(false);
        }}
        onOpenAssistant={() => {
          setAssistant(true);
        }}
      />
      <main id="contenido" className={styles.content} tabIndex={-1}>
        <ScreenErrorBoundary key={pathname}>
          <Outlet />
        </ScreenErrorBoundary>
      </main>
      {assistant && (
        <AssistantPanel
          onClose={() => {
            setAssistant(false);
          }}
        />
      )}
    </div>
  );
}
