import { Search } from "lucide-react";
import { useState, type SubmitEvent } from "react";

import type { OrderTab } from "../api/types";
import input from "../ui/Input.module.css";
import { withFilter } from "./orderParams";
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
  const [term, setTerm] = useState(params.get("q") ?? "");
  const search = (event: SubmitEvent) => {
    event.preventDefault();
    onParams(withFilter(params, "q", term.trim()));
  };
  return (
    <div className={styles.filters}>
      <form role="search" className={styles.search} onSubmit={search}>
        <Search size={16} aria-hidden="true" />
        <label htmlFor="buscar-comanda" className="visually-hidden">
          Buscar por cliente o número
        </label>
        <input
          id="buscar-comanda"
          type="search"
          placeholder="Buscar cliente o número de comanda"
          value={term}
          onChange={(event) => {
            setTerm(event.target.value);
          }}
        />
      </form>
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
