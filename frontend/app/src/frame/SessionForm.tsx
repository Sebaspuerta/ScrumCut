import type { ReactNode } from "react";

interface SessionFormProps {
  action: string;
  csrfToken: string | undefined;
  className: string | undefined;
  children: ReactNode;
}

/** Un POST a Django sobre la propia sesión (cerrar sesión), con el token CSRF; sin token aún, el botón espera. */
export function SessionForm({ action, csrfToken, className, children }: SessionFormProps) {
  return (
    <form method="post" action={action}>
      <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken ?? ""} />
      <button type="submit" className={className} disabled={!csrfToken}>
        {children}
      </button>
    </form>
  );
}
