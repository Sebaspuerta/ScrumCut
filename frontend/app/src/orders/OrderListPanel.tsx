import type { UseQueryResult } from "@tanstack/react-query";

import type { OrderList } from "../api/types";
import { StatusMessage } from "../frame/StatusMessage";
import { Pagination } from "../ui/Pagination";
import { OrderFilters } from "./OrderFilters";
import { PAGE_PARAM, withParam } from "./orderParams";
import styles from "./OrderList.module.css";
import { OrderRowLink } from "./OrderRowLink";

interface OrderListPanelProps {
  query: UseQueryResult<OrderList>;
  selected: string | null;
  params: URLSearchParams;
  onParams: (params: URLSearchParams) => void;
}

function Rows({ list, selected, params }: { list: OrderList; selected: string | null; params: URLSearchParams }) {
  if (list.results.length === 0) return <p className={styles.empty}>No hay comandas en esta pestaña.</p>;
  return (
    <ul className={styles.rows} aria-label="Comandas">
      {list.results.map((order) => (
        <li key={order.id}>
          <OrderRowLink order={order} selected={order.id === selected} params={params} />
        </li>
      ))}
    </ul>
  );
}

/** La lista de la pestaña con su búsqueda, sus estados de carga, vacío y error, y sus páginas. */
export function OrderListPanel({ query, selected, params, onParams }: OrderListPanelProps) {
  const list = query.data;
  return (
    <section className={styles.panel} aria-label="Lista de comandas" aria-busy={query.isFetching}>
      <OrderFilters params={params} tab={list?.tab ?? null} day={list?.day ?? null} onParams={onParams} />
      {query.isPending && <StatusMessage kind="loading">Cargando las comandas…</StatusMessage>}
      {query.isError && (
        <StatusMessage kind="error" onRetry={() => void query.refetch()}>
          No pudimos cargar las comandas.
        </StatusMessage>
      )}
      {list && <Rows list={list} selected={selected} params={params} />}
      {list && (
        <Pagination
          page={list.page}
          pages={list.pages}
          count={list.count}
          pageSize={list.page_size}
          label="Páginas de comandas"
          onPage={(page) => {
            onParams(withParam(params, PAGE_PARAM, String(page)));
          }}
        />
      )}
    </section>
  );
}
