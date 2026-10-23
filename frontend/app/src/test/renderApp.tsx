import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { AppRoutes } from "../AppRoutes";
import { createQueryClient } from "../queryClient";

/** La app completa en una ruta, con un QueryClient nuevo (sin caché entre pruebas). */
export function renderApp(path = "/") {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
