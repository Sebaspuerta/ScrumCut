import type { OrderTab } from "../api/types";
import { withFilter } from "../lib/searchParams";
import input from "../ui/Input.module.css";
import { SearchBox } from "../ui/SearchBox";
import styles from "./OrderList.module.css";

interface OrderFiltersProps {
  params: URLSearchParams;
  tab: OrderTab | null;
  /** El día de las cerradas y las anuladas, tal como lo resolvió el servidor. */
  day: string | null;
  onParams: (params: URLSearchParams) => void;
}

/** Búsqueda por cliente o número (al enviar) y, en cerradas y anuladas, el día. Todo queda en la URL. */
export function OrderFilters({ params, tab, day, onParams }: OrderFiltersProps) {
  return (
    <div className={styles.filters}>
      <SearchBox
        label="Buscar por cliente o número"
        placeholder="Buscar cliente o número de comanda"
        initial={params.get("q") ?? ""}
        onSearch={(term) => {
          onParams(withFilter(params, "q", term));
        }}
      />
      {tab !== null && tab !== "abiertas" && (
        <label className={styles.day}>
          <span>Día</span>
          <input
            className={input.input}
            type="date"
            value={params.get("fecha") ?? day ?? ""}
            onChange={(event) => {
              onParams(withFilter(params, "fecha", event.target.value));
            }}
          />
        </label>
      )}
    </div>
  );
}
