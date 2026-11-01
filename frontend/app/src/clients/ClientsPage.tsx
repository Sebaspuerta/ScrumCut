import { useSearchParams } from "react-router";

import type { ClientDetail, ClientList } from "../api/types";
import { StatusMessage } from "../frame/StatusMessage";
import { useClient, useClients } from "../hooks/useClients";
import { useMe } from "../hooks/useMe";
import { CLIENT_PARAM } from "../lib/appRoutes";
import { listQuery, withParam } from "../lib/searchParams";
import { ClientDetailPanel } from "./ClientDetailPanel";
import { ClientFormDialog } from "./ClientFormDialog";
import { ClientListPanel } from "./ClientListPanel";
import { EDIT_PARAM, FILTER_KEYS, NEW_PARAM } from "./clientParams";
import styles from "./Clients.module.css";
import { ClientStats } from "./ClientStats";
import { ClientsTitle } from "./ClientsTitle";
import { NoPolicyDialog } from "./NoPolicyDialog";

interface DialogsProps {
  list: ClientList | undefined;
  selected: string | null;
  params: URLSearchParams;
  onParams: (params: URLSearchParams) => void;
}

/** Nuevo cliente (?nuevo=1) y editar al elegido (?editar=1): los dos en la URL. */
function Dialogs({ list, selected, params, onParams }: DialogsProps) {
  const editing = useClient(params.get(EDIT_PARAM) === null ? null : selected).data;
  const close = (key: string) => () => {
    onParams(withParam(params, key, null));
  };
  const saved = (client: ClientDetail) => {
    onParams(withParam(withParam(withParam(params, NEW_PARAM, null), EDIT_PARAM, null), CLIENT_PARAM, client.id));
  };
  if (params.get(NEW_PARAM) !== null && list) {
    if (list.data_policy === null) return <NoPolicyDialog onClose={close(NEW_PARAM)} />;
    return <ClientFormDialog target={{ policy: list.data_policy }} onClose={close(NEW_PARAM)} onSaved={saved} />;
  }
  if (editing?.actions.edit) {
    return <ClientFormDialog target={{ client: editing }} onClose={close(EDIT_PARAM)} onSaved={saved} />;
  }
  return null;
}

/** Clientes: las cifras de la sede, la lista con sus filtros y la ficha del elegido. Todo va en la URL. */
export function ClientsPage() {
  const me = useMe();
  const [params, setParams] = useSearchParams();
  const permissions = me.data?.permissions ?? [];
  const allowed = permissions.includes("clientes.ver");
  const clients = useClients(listQuery(params, FILTER_KEYS), allowed);
  const selected = params.get(CLIENT_PARAM);
  const branch = me.data?.branch?.current_label ?? "";
  if (!allowed) return <StatusMessage kind="empty">Tu rol no tiene acceso a los clientes.</StatusMessage>;
  return (
    <>
      <ClientsTitle
        branch={branch}
        canCreate={permissions.includes("clientes.crear")}
        onCreate={() => {
          setParams(withParam(params, NEW_PARAM, "1"));
        }}
      />
      {clients.data && <ClientStats stats={clients.data.stats} />}
      <div className={styles.split}>
        <ClientListPanel query={clients} selected={selected} branch={branch} params={params} onParams={setParams} />
        {selected ? (
          <ClientDetailPanel
            key={selected}
            id={selected}
            branch={branch}
            onEdit={() => {
              setParams(withParam(params, EDIT_PARAM, "1"));
            }}
            onClose={() => {
              setParams(withParam(withParam(params, CLIENT_PARAM, null), EDIT_PARAM, null));
            }}
          />
        ) : (
          <section className={styles.panel} aria-label="Ficha del cliente">
            <p className={styles.muted}>Elige un cliente de la lista para ver su ficha en esta sede.</p>
          </section>
        )}
      </div>
      <Dialogs list={clients.data} selected={selected} params={params} onParams={setParams} />
    </>
  );
}
