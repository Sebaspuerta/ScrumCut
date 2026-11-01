import type { ClientList } from "../api/types";
import { cx } from "../lib/cx";
import { withFilter } from "../lib/searchParams";
import input from "../ui/Input.module.css";
import { SearchBox } from "../ui/SearchBox";
import styles from "./Clients.module.css";
import { LevelFilter } from "./LevelFilter";

interface ClientFiltersProps {
  list: ClientList | undefined;
  params: URLSearchParams;
  onParams: (params: URLSearchParams) => void;
}

/** Búsqueda por nombre, celular o cédula, orden y nivel; todo en la URL y lo filtra el servidor. */
export function ClientFilters({ list, params, onParams }: ClientFiltersProps) {
  const set = (key: string) => (value: string) => {
    onParams(withFilter(params, key, value));
  };
  return (
    <>
      <div className={styles.filters}>
        <SearchBox
          label="Buscar cliente"
          placeholder="Nombre, celular o cédula"
          initial={params.get("q") ?? ""}
          onSearch={set("q")}
        />
        {list && (
          <select
            aria-label="Ordenar por"
            className={cx(input.input, styles.order)}
            value={list.order}
            onChange={(event) => {
              set("orden")(event.target.value);
            }}
          >
            {list.orderings.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        )}
      </div>
      {list && <LevelFilter levels={list.levels} current={list.level} onPick={set("nivel")} />}
    </>
  );
}
