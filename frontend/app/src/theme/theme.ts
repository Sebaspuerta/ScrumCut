// Tema de la interfaz. "system" no pone nada en <html> y manda prefers-color-scheme; "light" y "dark"
// van en data-theme, igual que en el HTML que entrega Django. Nada se guarda en el navegador.
import type { Theme } from "../api/types";

export const DARK_QUERY = "(prefers-color-scheme: dark)";

export type EffectiveTheme = "light" | "dark";

export function systemTheme(): EffectiveTheme {
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

export function effectiveTheme(theme: Theme): EffectiveTheme {
  return theme === "system" ? systemTheme() : theme;
}

/** El botón de la barra superior: pasa al contrario de lo que se ve ahora. */
export function toggledTheme(theme: Theme): EffectiveTheme {
  return effectiveTheme(theme) === "dark" ? "light" : "dark";
}

export function applyTheme(theme: Theme, root: HTMLElement = document.documentElement): void {
  if (theme === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", theme);
}
