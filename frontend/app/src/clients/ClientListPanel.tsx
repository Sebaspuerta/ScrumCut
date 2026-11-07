import type { UseQueryResult } from "@tanstack/react-query";

import type { ClientList } from "../api/types";
import { LoadError } from "../frame/LoadError";
import { StatusMessage } from "../frame/StatusMessage";
import { PAGE_PARAM, withParam } from "../lib/searchParams";
import { Pagination } from "../ui/Pagination";
import { ClientFilters } from "./ClientFilters";
import styles from "./Clients.module.css";
import { ClientTable } from "./ClientTable";

interface ClientListPanelProps {
  query: UseQueryResult<ClientList>;
  selected: string | null;
  branch: string;
  params: URLSearchParams;
  onParams: (params: URLSearchParams) => void;
}

/** La lista de la sede con sus filtros, sus estados de carga, vacío y error, y sus páginas. */
export function ClientListPanel({ query, selected, branch, params, onParams }: ClientListPanelProps) {
  const list = query.data;
  return (
    <section className={styles.list} aria-label="Lista de clientes" aria-busy={query.isFetching}>
      <ClientFilters list={list} params={params} onParams={onParams} />
      {query.isPending && <StatusMessage kind="loading">Cargando los clientes…</StatusMessage>}
      {query.isError && (
        <LoadError error={query.error} onRetry={() => void query.refetch()}>
          No pudimos cargar los clientes.
        </LoadError>
      )}
      {list && <ClientTable rows={list.results} selected={selected} params={params} branch={branch} />}
      {list && (
        <Pagination
          page={list.page}
          pages={list.pages}
          count={list.count}
          pageSize={list.page_size}
          label="Páginas de clientes"
          onPage={(page) => {
            onParams(withParam(params, PAGE_PARAM, String(page)));
          }}
        />
      )}
    </section>
  );
}
