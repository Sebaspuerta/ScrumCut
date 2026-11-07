import { useId } from "react";

import type { Access } from "../api/types";
import { Logo } from "../brand/Logo";
import { useCsrfToken } from "../hooks/useCsrfToken";
import { DJANGO_ROUTES } from "../lib/djangoRoutes";
import { buttonClass } from "../ui/Button";
import styles from "./AccessPage.module.css";
import { accessCopy } from "./accessCopy";
import { SessionForm } from "./SessionForm";

interface AccessPageProps {
  access: Access;
}

/** Sin una barbería activa: qué pasó, qué hacer y cómo salir. Nunca nombra otra barbería que la propia. */
export function AccessPage({ access }: AccessPageProps) {
  const titleId = useId();
  const csrf = useCsrfToken();
  const { title, body } = accessCopy(access);
  return (
    <main className={styles.page}>
      <Logo />
      <section className={styles.panel} aria-labelledby={titleId}>
        <h1 id={titleId}>{title}</h1>
        <p>{body}</p>
        <SessionForm action={DJANGO_ROUTES.logout} csrfToken={csrf.data} className={buttonClass("primary")}>
          Cerrar sesión
        </SessionForm>
      </section>
    </main>
  );
}
