import type { ButtonHTMLAttributes, ReactNode } from "react";

import styles from "./Button.module.css";

export type ButtonKind = "primary" | "secondary" | "text";

export function buttonClass(kind: ButtonKind, block = false): string {
  return [styles.button, styles[kind], block ? styles.block : ""].join(" ");
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  kind?: ButtonKind;
  block?: boolean;
  children: ReactNode;
}

/** Botón de la identidad: principal (acento), secundario (borde) o de texto. */
export function Button({
  kind = "primary",
  block = false,
  type = "button",
  className = "",
  children,
  ...rest
}: ButtonProps) {
  return (
    <button type={type} className={`${buttonClass(kind, block)} ${className}`} {...rest}>
      {children}
    </button>
  );
}
