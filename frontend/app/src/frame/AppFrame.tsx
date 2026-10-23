import { useState } from "react";
import { Outlet } from "react-router";

import { useMe } from "../hooks/useMe";
import { useNavigation } from "../hooks/useNavigation";
import styles from "./AppFrame.module.css";
import { AssistantPanel } from "./AssistantPanel";
import { Sidebar } from "./Sidebar";
import { StatusMessage } from "./StatusMessage";
import { TopBar } from "./TopBar";

/** El marco de la app: barra superior y barra lateral, armadas solo con lo que entregan me y navigation. */
export function AppFrame() {
  const me = useMe();
  const navigation = useNavigation(me.data?.barbershop != null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [assistant, setAssistant] = useState(false);

  if (me.isPending) return <StatusMessage kind="loading">Cargando tu cuenta…</StatusMessage>;
  if (me.isError) {
    return (
      <StatusMessage kind="error" onRetry={() => void me.refetch()}>
        No pudimos cargar tu cuenta.
      </StatusMessage>
    );
  }
  const { barbershop, branch } = me.data;
  if (barbershop === null || branch === null) {
    return (
      <StatusMessage kind="empty">
        Tu cuenta no tiene una barbería activa. <a href="/">Ir al inicio</a>
      </StatusMessage>
    );
  }
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
        <Outlet />
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
