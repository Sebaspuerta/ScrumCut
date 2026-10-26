import { useSearchParams } from "react-router";

import { StaleCashNotice } from "../cash/StaleCashNotice";
import { StatusMessage } from "../frame/StatusMessage";
import { useMe } from "../hooks/useMe";
import { useOrders } from "../hooks/useOrders";
import { Notice } from "../ui/Notice";
import { NewOrderDialog } from "./NewOrderDialog";
import { listQuery, NEW_PARAM, ORDER_PARAM, withParam } from "./orderParams";
import { OrderDetailPanel } from "./OrderDetailPanel";
import { OrderListPanel } from "./OrderListPanel";
import { OrdersTitle } from "./OrdersTitle";
import styles from "./OrdersPage.module.css";
import { OrderTabs } from "./OrderTabs";
import { SidePlaceholder } from "./SidePlaceholder";

const ALL_BRANCHES_NOTICE =
  "Estás viendo todas las sedes: para crear o cobrar una comanda, elige una sede en la barra superior.";

/** Comandas: la lista por pestañas a la izquierda y la comanda elegida a la derecha. Todo va en la URL. */
export function OrdersPage() {
  const me = useMe();
  const [params, setParams] = useSearchParams();
  const permissions = me.data?.permissions ?? [];
  const allowed = permissions.includes("comandas.ver");
  const orders = useOrders(listQuery(params), allowed);
  const selected = params.get(ORDER_PARAM);
  const oneBranch = me.data?.branch?.mode === "una";
  const canCreate = oneBranch && permissions.includes("comandas.crear");

  if (!allowed) return <StatusMessage kind="empty">Tu rol no tiene acceso a las comandas.</StatusMessage>;
  const open = (id: string | null) => {
    setParams(withParam(params, ORDER_PARAM, id));
  };
  return (
    <>
      <OrdersTitle
        branch={me.data?.branch?.current_label ?? ""}
        day={orders.data?.day ?? null}
        canCreate={canCreate}
        canQuickCharge={oneBranch && permissions.includes("comandas.cerrar")}
        onCreate={() => {
          setParams(withParam(params, NEW_PARAM, "1"));
        }}
      />
      {!oneBranch && <Notice>{ALL_BRANCHES_NOTICE}</Notice>}
      {orders.data?.stale_cash && <StaleCashNotice />}
      {orders.data && <OrderTabs tabs={orders.data.tabs} current={orders.data.tab} params={params} />}
      <div className={styles.split}>
        <OrderListPanel query={orders} selected={selected} params={params} onParams={setParams} />
        {selected ? (
          <OrderDetailPanel
            key={selected}
            id={selected}
            onClose={() => {
              open(null);
            }}
          />
        ) : (
          <SidePlaceholder list={orders.data} />
        )}
      </div>
      {canCreate && params.get(NEW_PARAM) !== null && (
        <NewOrderDialog
          onClose={() => {
            setParams(withParam(params, NEW_PARAM, null));
          }}
          onCreated={(id) => {
            setParams(withParam(withParam(params, NEW_PARAM, null), ORDER_PARAM, id));
          }}
        />
      )}
    </>
  );
}
