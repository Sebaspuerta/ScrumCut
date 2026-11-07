import type { UseQueryResult } from "@tanstack/react-query";

import type { ProductList } from "../api/types";
import { LoadError } from "../frame/LoadError";
import { StatusMessage } from "../frame/StatusMessage";
import { PAGE_PARAM, withParam } from "../lib/searchParams";
import { Pagination } from "../ui/Pagination";
import styles from "./Inventory.module.css";
import { ProductFilters } from "./ProductFilters";
import { ProductTable } from "./ProductTable";

interface ProductListPanelProps {
  query: UseQueryResult<ProductList>;
  selected: string | null;
  branch: string;
  allBranches: boolean;
  params: URLSearchParams;
  onParams: (params: URLSearchParams) => void;
}

/** El catálogo con sus filtros, sus estados de carga, vacío y error, y sus páginas. */
export function ProductListPanel({ query, selected, branch, allBranches, params, onParams }: ProductListPanelProps) {
  const list = query.data;
  return (
    <section className={styles.list} aria-label="Lista de productos" aria-busy={query.isFetching}>
      <ProductFilters list={list} params={params} onParams={onParams} />
      {query.isPending && <StatusMessage kind="loading">Cargando los productos…</StatusMessage>}
      {query.isError && (
        <LoadError error={query.error} onRetry={() => void query.refetch()}>
          No pudimos cargar los productos.
        </LoadError>
      )}
      {list && (
        <ProductTable
          rows={list.results}
          selected={selected}
          params={params}
          branch={branch}
          allBranches={allBranches}
        />
      )}
      {list && (
        <Pagination
          page={list.page}
          pages={list.pages}
          count={list.count}
          pageSize={list.page_size}
          label="Páginas de productos"
          onPage={(page) => {
            onParams(withParam(params, PAGE_PARAM, String(page)));
          }}
        />
      )}
    </section>
  );
}
