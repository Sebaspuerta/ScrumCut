import { Component, type ReactNode } from "react";

import { StatusMessage } from "./StatusMessage";

interface ScreenErrorBoundaryProps {
  children: ReactNode;
}

interface ScreenErrorBoundaryState {
  failed: boolean;
}

/** Un fallo inesperado de una pantalla deja en pie el marco: aviso, "Reintentar" y "Volver al inicio", sin la pila.
 *
 * Es una clase porque React solo atrapa los errores de render en una (no hay hook para eso). El marco le cambia
 * la `key` con la ruta, así que al navegar se vuelve a intentar.
 */
export class ScreenErrorBoundary extends Component<ScreenErrorBoundaryProps, ScreenErrorBoundaryState> {
  override state: ScreenErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): ScreenErrorBoundaryState {
    return { failed: true };
  }

  private readonly retry = () => {
    this.setState({ failed: false });
  };

  override render() {
    if (!this.state.failed) return this.props.children;
    return (
      <StatusMessage kind="error" onRetry={this.retry} homeLink>
        Algo salió mal en esta pantalla.
      </StatusMessage>
    );
  }
}
