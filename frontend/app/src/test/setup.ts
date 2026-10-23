import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

// jsdom no trae matchMedia: el sistema operativo de las pruebas está en modo claro salvo que una prueba lo cambie.
function fakeMatchMedia(query: string): Partial<MediaQueryList> {
  return {
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  };
}

beforeEach(() => {
  vi.stubGlobal("matchMedia", fakeMatchMedia);
});

afterEach(() => {
  // La prueba de los tipos generados corre en Node, sin DOM.
  if (typeof document === "undefined") return;
  cleanup();
  document.documentElement.removeAttribute("data-theme");
});
