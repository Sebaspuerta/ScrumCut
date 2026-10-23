import { useSearchParams } from "react-router";

import { StatusMessage } from "../frame/StatusMessage";
import { useDashboard } from "../hooks/useDashboard";
import { useMe } from "../hooks/useMe";
import { AlertsPanel } from "./AlertsPanel";
import { BarbersPanel } from "./BarbersPanel";
import { CashPanel } from "./CashPanel";
import { ClosingsPanel } from "./ClosingsPanel";
import styles from "./DashboardPage.module.css";
import { DashboardSkeleton } from "./DashboardSkeleton";
import { DashboardTitle } from "./DashboardTitle";
import { MetricStrip } from "./MetricStrip";
import { ProductsPanel } from "./ProductsPanel";
import { SalesPanel } from "./SalesPanel";
import { StaleCashNotice } from "./StaleCashNotice";

const REPORTS_PERMISSION = "reportes.ver";

/** Tablero "Resumen ejecutivo". El mes (?mes=) y la vista (?vista=3d) van en la URL, nunca en el navegador. */
export function DashboardPage() {
  const me = useMe();
  const [params] = useSearchParams();
  const allowed = me.data?.permissions.includes(REPORTS_PERMISSION) ?? false;
  const dashboard = useDashboard(params.get("mes"), allowed);

  if (!allowed) {
    return (
      <StatusMessage kind="empty">
        El resumen ejecutivo es para quien ve los reportes. Tus cortes de hoy siguen en el{" "}
        <a href="/">tablero actual</a>.
      </StatusMessage>
    );
  }
  if (dashboard.isPending) return <DashboardSkeleton />;
  if (dashboard.isError) {
    return (
      <StatusMessage kind="error" onRetry={() => void dashboard.refetch()}>
        No pudimos cargar el tablero.
      </StatusMessage>
    );
  }
  const data = dashboard.data;
  const permissions = me.data?.permissions ?? [];
  return (
    <>
      <DashboardTitle
        data={data}
        updatedAt={dashboard.dataUpdatedAt}
        refreshing={dashboard.isFetching}
        canExport={permissions.includes("reportes.exportar")}
        onRefresh={() => void dashboard.refetch()}
      />
      {data.stale_cash && <StaleCashNotice />}
      <MetricStrip data={data} />
      <div className={styles.gridMain}>
        <SalesPanel data={data} view={params.get("vista") === "3d" ? "3d" : "calendar"} />
        <CashPanel cash={data.cash} canOpenCash={permissions.includes("caja.ver")} timeZone={data.timezone} />
      </div>
      <div className={styles.gridLower}>
        <BarbersPanel barbers={data.barbers} />
        <AlertsPanel alerts={data.alerts} unread={data.unread_alerts} timeZone={data.timezone} />
      </div>
      <div className={styles.gridLower}>
        <ProductsPanel products={data.products} />
        <ClosingsPanel closings={data.closings} />
      </div>
    </>
  );
}
