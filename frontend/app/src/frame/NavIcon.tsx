import { createElement } from "react";
import type { LucideProps } from "lucide-react";

import { navIcon } from "./navIcons";

interface NavIconProps extends Omit<LucideProps, "name"> {
  name: string | null;
}

/** El ícono de lucide-react que corresponde al nombre que entrega la API (un mapa fijo, no un componente nuevo). */
export function NavIcon({ name, ...props }: NavIconProps) {
  return createElement(navIcon(name), { "aria-hidden": true, ...props });
}
