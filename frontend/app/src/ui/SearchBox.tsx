import { Search } from "lucide-react";
import { useId, useState, type SubmitEvent } from "react";

import styles from "./SearchBox.module.css";

interface SearchBoxProps {
  label: string;
  placeholder: string;
  initial: string;
  /** Al enviar (Enter): el término queda en la URL y lo filtra el servidor. */
  onSearch: (term: string) => void;
}

/** El buscador de una lista, con su ícono y su etiqueta para el lector de pantalla. */
export function SearchBox({ label, placeholder, initial, onSearch }: SearchBoxProps) {
  const id = useId();
  const [term, setTerm] = useState(initial);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    onSearch(term.trim());
  };
  return (
    <form role="search" className={styles.search} onSubmit={submit}>
      <Search size={16} aria-hidden="true" />
      <label htmlFor={id} className="visually-hidden">
        {label}
      </label>
      <input
        id={id}
        type="search"
        placeholder={placeholder}
        value={term}
        onChange={(event) => {
          setTerm(event.target.value);
        }}
      />
    </form>
  );
}
