import { Search } from "lucide-react";
import { useId, useState, type KeyboardEvent } from "react";

import { Dialog } from "../ui/Dialog";
import { filterCommands, nextEnabled, type Command } from "./commands";
import styles from "./CommandPalette.module.css";
import { NavIcon } from "./NavIcon";

interface CommandPaletteProps {
  commands: Command[];
  onRun: (command: Command) => void;
  onClose: () => void;
}

/** Buscar (Ctrl K): flechas para moverse, Enter para abrir y Esc para cerrar. */
export function CommandPalette({ commands, onRun, onClose }: CommandPaletteProps) {
  const listId = useId();
  const [query, setQuery] = useState("");
  const shown = filterCommands(commands, query);
  const [active, setActive] = useState(() => nextEnabled(shown, -1, 1));
  const current = shown[active];

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setActive(nextEnabled(shown, active, event.key === "ArrowDown" ? 1 : -1));
    } else if (event.key === "Enter" && current?.target) {
      event.preventDefault();
      onRun(current);
    }
  };
  const search = (text: string) => {
    setQuery(text);
    setActive(nextEnabled(filterCommands(commands, text), -1, 1));
  };

  return (
    <Dialog label="Buscar en ScrumCut" onClose={onClose} placement="top" className={styles.palette}>
      <div className={styles.search}>
        <Search size={19} aria-hidden="true" />
        <input
          role="combobox"
          aria-expanded="true"
          aria-controls={listId}
          aria-activedescendant={current?.target ? `${listId}-${current.id}` : undefined}
          aria-label="Buscar pantallas y acciones"
          placeholder="Buscar clientes, comandas y acciones…"
          value={query}
          onChange={(event) => {
            search(event.target.value);
          }}
          onKeyDown={onKeyDown}
        />
        <kbd>ESC</kbd>
      </div>
      <ul id={listId} role="listbox" aria-label="Sugerencias" className={styles.list}>
        {shown.length === 0 && <li className={styles.empty}>Nada coincide con «{query}».</li>}
        {shown.map((command, index) => {
          return (
            <li
              key={command.id}
              id={`${listId}-${command.id}`}
              role="option"
              aria-selected={index === active}
              aria-disabled={command.target === null}
              className={styles.option}
              onMouseDown={(event) => {
                event.preventDefault();
                if (command.target) onRun(command);
              }}
            >
              <NavIcon name={command.icon} size={18} />
              <span className={styles.text}>
                <b>{command.label}</b>
                <small>
                  {command.group} · {command.note}
                </small>
              </span>
            </li>
          );
        })}
      </ul>
      <footer className={styles.footer}>
        <span>
          <kbd>↑</kbd> <kbd>↓</kbd> para navegar
        </span>
        <span>
          <kbd>↵</kbd> para abrir
        </span>
      </footer>
    </Dialog>
  );
}
