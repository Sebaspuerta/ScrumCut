import type { Option, ProductList } from "../api/types";
import { cx } from "../lib/cx";
import { withFilter } from "../lib/searchParams";
import input from "../ui/Input.module.css";
import { SearchBox } from "../ui/SearchBox";
import styles from "./Inventory.module.css";

interface ProductFiltersProps {
  list: ProductList | undefined;
  params: URLSearchParams;
  onParams: (params: URLSearchParams) => void;
}

const UNCATEGORIZED: Option = { value: "sin", label: "Sin categoría" };

interface FilterSelectProps {
  label: string;
  all: string;
  value: string;
  options: Option[];
  onPick: (value: string) => void;
}

function FilterSelect({ label, all, value, options, onPick }: FilterSelectProps) {
  return (
    <select
      aria-label={label}
      className={cx(input.input, styles.filter)}
      value={value}
      onChange={(event) => {
        onPick(event.target.value);
      }}
    >
      {all && <option value="">{all}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

/** Búsqueda por nombre o proveedor, categoría, tipo y estado; todo en la URL y lo filtra el servidor. */
export function ProductFilters({ list, params, onParams }: ProductFiltersProps) {
  const set = (key: string) => (value: string) => {
    onParams(withFilter(params, key, value));
  };
  return (
    <div className={styles.filters}>
      <SearchBox
        label="Buscar producto"
        placeholder="Nombre o proveedor"
        initial={params.get("q") ?? ""}
        onSearch={set("q")}
      />
      {list && (
        <>
          <FilterSelect
            label="Categoría"
            all="Todas las categorías"
            value={list.category}
            options={[...list.categories, UNCATEGORIZED]}
            onPick={set("categoria")}
          />
          <FilterSelect
            label="Tipo"
            all="Todos los tipos"
            value={list.product_type}
            options={list.types}
            onPick={set("tipo")}
          />
          <FilterSelect label="Estado" all="" value={list.status} options={list.statuses} onPick={set("estado")} />
        </>
      )}
    </div>
  );
}
