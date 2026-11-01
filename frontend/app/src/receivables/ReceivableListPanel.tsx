import type { UseQueryResult } from "@tanstack/react-query";

import type { ReceivableList } from "../api/types";
import { StatusMessage } from "../frame/StatusMessage";
import { RECEIVABLE_PARAM } from "../lib/appRoutes";
import { PAGE_PARAM, withFilter, withParam } from "../lib/searchParams";
import { Pagination } from "../ui/Pagination";
import { SearchBox } from "../ui/SearchBox";
import { TabLinks } from "../ui/TabLinks";
import styles from "./Receivables.module.css";
import { ReceivableTable } from "./ReceivableTable";

interface ReceivableListPanelProps {
  query: UseQueryResult<ReceivableList>;
  selected: string | null;
  branch: string;
  params: URLSearchParams;
  onParams: (params: URLSearchParams) => void;
}

/** Pendientes, Vencidos y Pagados en el mes con su conteo, la búsqueda por cliente, la lista y sus páginas. */
export function ReceivableListPanel({ query, selected, branch, params, onParams }: ReceivableListPanelProps) {
  const list = query.data;
  const tabSearch = (value: string) => {
    const next = withFilter(params, "pestana", value);
    next.delete(RECEIVABLE_PARAM);
    return next.toString();
  };
  return (
    <section className={styles.list} aria-label="Lista de fiados" aria-busy={query.isFetching}>
      <div className={styles.filters}>
        {list && <TabLinks tabs={list.tabs} current={list.tab} label="Estado de los fiados" searchFor={tabSearch} />}
        <SearchBox
          label="Buscar cliente"
          placeholder="Buscar cliente"
          initial={params.get("q") ?? ""}
          onSearch={(term) => {
            onParams(withFilter(params, "q", term));
          }}
        />
      </div>
      {query.isPending && <StatusMessage kind="loading">Cargando los fiados…</StatusMessage>}
      {query.isError && (
        <StatusMessage kind="error" onRetry={() => void query.refetch()}>
          No pudimos cargar los fiados.
        </StatusMessage>
      )}
      {list && <ReceivableTable rows={list.results} selected={selected} params={params} branch={branch} />}
      {list && (
        <Pagination
          page={list.page}
          pages={list.pages}
          count={list.count}
          pageSize={list.page_size}
          label="Páginas de fiados"
          onPage={(page) => {
            onParams(withParam(params, PAGE_PARAM, String(page)));
          }}
        />
      )}
      <p className={styles.note}>
        Ordenados por urgencia: primero los más vencidos. Un fiado solo se abona en la sede donde se hizo.
      </p>
    </section>
  );
}
