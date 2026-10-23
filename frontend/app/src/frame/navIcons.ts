// Los íconos de la referencia (docs/diseno/figma-make) para cada nombre de ícono que entrega la API.
import {
  Banknote,
  BookOpen,
  Boxes,
  CalendarDays,
  ChartColumn,
  ClipboardList,
  CreditCard,
  Dot,
  LayoutDashboard,
  Star,
  Users,
  type LucideIcon,
} from "lucide-react";

const NAV_ICONS: Partial<Record<string, LucideIcon>> = {
  "layout-dashboard": LayoutDashboard,
  calendar: CalendarDays,
  receipt: ClipboardList,
  banknote: Banknote,
  users: Users,
  "notebook-pen": CreditCard,
  star: Star,
  tag: BookOpen,
  package: Boxes,
  "chart-column": ChartColumn,
  "git-compare-arrows": ChartColumn,
};

export function navIcon(name: string | null): LucideIcon {
  return (name === null ? undefined : NAV_ICONS[name]) ?? Dot;
}
