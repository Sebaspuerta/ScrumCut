import { useEffect, useRef, type ReactNode } from "react";

import styles from "./Dialog.module.css";

const FOCUSABLE = "a[href], button:not(:disabled), input:not(:disabled), select, [tabindex='0']";

interface DialogProps {
  label: string;
  onClose: () => void;
  /** "top": la paleta de comandos, arriba; "center": paneles como Administración. */
  placement?: "center" | "top";
  className?: string | undefined;
  children: ReactNode;
}

function keepFocusInside(event: KeyboardEvent, box: HTMLElement) {
  const focusable = [...box.querySelectorAll<HTMLElement>(FOCUSABLE)];
  const [first, last] = [focusable[0], focusable.at(-1)];
  if (!first || !last) return;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

/** Diálogo modal: lleva el foco adentro, Esc o un clic en el fondo lo cierran y el foco vuelve a donde estaba. */
export function Dialog({ label, onClose, placement = "center", className = "", children }: DialogProps) {
  const boxRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  useEffect(() => {
    closeRef.current = onClose;
  });

  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const box = boxRef.current;
    box?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeRef.current();
      else if (event.key === "Tab" && box) keepFocusInside(event, box);
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, []);

  return (
    <div
      className={[styles.scrim, placement === "top" ? styles.top : ""].join(" ")}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div ref={boxRef} role="dialog" aria-modal="true" aria-label={label} className={className}>
        {children}
      </div>
    </div>
  );
}
