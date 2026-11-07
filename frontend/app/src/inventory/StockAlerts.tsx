import { LoadError } from "../frame/LoadError";
import { useStockAlerts } from "../hooks/useInventory";
import styles from "./Inventory.module.css";
import { StockAlertList } from "./StockAlertList";

/** Stock bajo y por vencer en la sede, arriba de la lista. Mientras cargan no ocupan lugar. */
export function StockAlerts() {
  const alerts = useStockAlerts(true);
  if (alerts.isError) {
    return (
      <LoadError error={alerts.error} onRetry={() => void alerts.refetch()}>
        No pudimos cargar los avisos de inventario.
      </LoadError>
    );
  }
  if (!alerts.data) return null;
  const { low_stock, low_stock_count, expiring, expiring_count } = alerts.data;
  return (
    <div className={styles.alerts}>
      <StockAlertList
        title="Stock bajo"
        kind="low"
        items={low_stock}
        count={low_stock_count}
        empty="Ningún producto está en su mínimo o por debajo."
      />
      <StockAlertList
        title="Por vencer"
        kind="expiring"
        items={expiring}
        count={expiring_count}
        empty="Ningún perecedero vence en los próximos 30 días."
      />
    </div>
  );
}
