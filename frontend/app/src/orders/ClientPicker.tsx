import { Search } from "lucide-react";
import { useState, type SubmitEvent } from "react";

import type { ClientChoice } from "../api/types";
import { useClientSearch } from "../hooks/useOrders";
import { Button } from "../ui/Button";
import input from "../ui/Input.module.css";
import styles from "./ClientPicker.module.css";

interface ClientPickerProps {
  selected: ClientChoice | null;
  onPick: (client: ClientChoice) => void;
}

function Results({ term, selected, onPick }: { term: string } & ClientPickerProps) {
  const search = useClientSearch(term);
  if (!term) return null;
  if (search.isPending) return <p className={styles.note}>Buscando…</p>;
  if (search.isError) return <p className={styles.note}>No pudimos buscar. Intenta de nuevo.</p>;
  if (search.data.length === 0) return <p className={styles.note}>Ningún cliente coincide con «{term}».</p>;
  return (
    <ul className={styles.results} aria-label="Clientes encontrados">
      {search.data.map((client) => (
        <li key={client.id}>
          <button
            type="button"
            className={styles.result}
            aria-pressed={selected?.id === client.id}
            onClick={() => {
              onPick(client);
            }}
          >
            <b>{client.name}</b>
            {client.phone && <small>{client.phone}</small>}
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Buscar un cliente de la barbería por nombre, celular o documento: solo nombre y celular enmascarado. */
export function ClientPicker({ selected, onPick }: ClientPickerProps) {
  const [text, setText] = useState("");
  const [term, setTerm] = useState("");
  const search = (event: SubmitEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setTerm(text.trim());
  };
  return (
    <div className={styles.picker}>
      <form role="search" className={styles.search} onSubmit={search}>
        <label htmlFor="buscar-cliente" className="visually-hidden">
          Buscar cliente por nombre, celular o documento
        </label>
        <input
          id="buscar-cliente"
          data-autofocus
          className={input.input}
          type="search"
          placeholder="Nombre, celular o documento"
          value={text}
          onChange={(event) => {
            setText(event.target.value);
          }}
        />
        <Button kind="secondary" type="submit">
          <Search size={16} aria-hidden="true" />
          Buscar
        </Button>
      </form>
      <Results term={term} selected={selected} onPick={onPick} />
    </div>
  );
}
