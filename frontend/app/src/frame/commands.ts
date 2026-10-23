// Lo que ofrece la paleta de comandos (Ctrl K): solo la navegación y las acciones de "+ Nuevo" que la API
// entrega para el rol. La búsqueda de clientes y comandas espera su endpoint: sale como "Próximamente".
import type { Navigation, NavItem } from "../api/types";

export interface Command {
  id: string;
  label: string;
  note: string;
  group: string;
  icon: string | null;
  /** Ruta de la app de React o URL de una pantalla de Django; null mientras no exista. */
  target: { app: string } | { url: string } | null;
}

const UPCOMING_SEARCHES: Command[] = [
  { id: "buscar-cliente", label: "Buscar cliente", note: "Próximamente", group: "Buscar", icon: "users", target: null },
  {
    id: "buscar-comanda",
    label: "Buscar comanda",
    note: "Próximamente",
    group: "Buscar",
    icon: "receipt",
    target: null,
  },
];

function targetOf(item: NavItem): Command["target"] {
  if (item.app_path !== null) return { app: item.app_path };
  return item.url === null ? null : { url: item.url };
}

function fromItem(item: NavItem, group: string, note: string): Command {
  return { id: `${group}-${item.label}`, label: item.label, note, group, icon: item.icon, target: targetOf(item) };
}

export function buildCommands(navigation: Navigation): Command[] {
  const screens = navigation.sidebar.flatMap((group) =>
    group.items.filter((item) => targetOf(item) !== null).map((item) => fromItem(item, "Ir a", group.title)),
  );
  const actions = navigation.new_actions.map((item) => fromItem(item, "Acciones", "Acción rápida"));
  return [...actions, ...screens, ...UPCOMING_SEARCHES];
}

const simplify = (text: string) =>
  text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();

/** Coincide sin tildes ni mayúsculas con el nombre o la nota. */
export function filterCommands(commands: Command[], query: string): Command[] {
  const wanted = simplify(query.trim());
  if (!wanted) return commands;
  return commands.filter((command) => simplify(`${command.label} ${command.note}`).includes(wanted));
}

/** El siguiente comando que se puede abrir, en la dirección de la flecha y dando la vuelta. */
export function nextEnabled(commands: Command[], from: number, step: 1 | -1): number {
  const enabled = commands.some((command) => command.target !== null);
  if (!enabled) return -1;
  let index = from;
  do {
    index = (index + step + commands.length) % commands.length;
  } while (commands[index]?.target === null);
  return index;
}
