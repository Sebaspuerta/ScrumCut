import { useEffect, useRef } from "react";

interface Hotkey {
  key: string;
  /** Ctrl en Windows y Linux, Cmd en Mac. */
  withCommand?: boolean;
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

/** Un atajo de teclado global. Las teclas sueltas (N) no cuentan mientras se escribe en un campo. */
export function useHotkey({ key, withCommand = false }: Hotkey, onPress: () => void) {
  const handler = useRef(onPress);
  useEffect(() => {
    handler.current = onPress;
  });
  useEffect(() => {
    const listen = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() !== key.toLowerCase()) return;
      const command = event.ctrlKey || event.metaKey;
      if (command !== withCommand || event.altKey) return;
      if (!withCommand && isTyping(event.target)) return;
      event.preventDefault();
      handler.current();
    };
    window.addEventListener("keydown", listen);
    return () => {
      window.removeEventListener("keydown", listen);
    };
  }, [key, withCommand]);
}
