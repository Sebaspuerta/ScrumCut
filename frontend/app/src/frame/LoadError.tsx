import type { ReactNode } from "react";

import { loadProblem } from "../api/errors";
import { StatusMessage } from "./StatusMessage";

interface LoadErrorProps {
  error: Error | null;
  /** El aviso de la pantalla para un error del servidor o desconocido. */
  children: ReactNode;
  onRetry?: () => void;
}

/** El error de una lectura según su código: sin permiso, demasiadas peticiones, sin conexión o el de la pantalla. */
export function LoadError({ error, children, onRetry }: LoadErrorProps) {
  const problem = loadProblem(error);
  return (
    <StatusMessage kind="error" onRetry={problem.retry ? onRetry : undefined}>
      {problem.message ?? children}
    </StatusMessage>
  );
}
