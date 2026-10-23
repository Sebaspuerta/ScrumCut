import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

function useDismiss(
  open: boolean,
  close: () => void,
  container: RefObject<HTMLDivElement | null>,
  trigger: RefObject<HTMLButtonElement | null>,
) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      close();
      trigger.current?.focus();
    };
    const onPointer = (event: MouseEvent) => {
      if (!container.current?.contains(event.target as Node)) close();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onPointer);
    };
  }, [open, close, container, trigger]);
}

/** Un menú que se abre bajo su botón: Esc lo cierra y devuelve el foco al botón; un clic fuera, también. */
export function usePopover() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => {
    setOpen(false);
  }, []);
  const toggle = useCallback(() => {
    setOpen((current) => !current);
  }, []);
  useDismiss(open, close, containerRef, triggerRef);
  return { open, close, toggle, containerRef, triggerRef };
}
