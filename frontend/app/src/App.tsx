import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";

import { AppRoutes } from "./AppRoutes";
import { createQueryClient } from "./queryClient";
import { BASENAME } from "./routes";

const queryClient = createQueryClient();

// Enrutador declarativo: los datos los trae TanStack Query, así que no hace falta el enrutador de datos
// (createBrowserRouter), que además guarda en el navegador las transiciones de vista (AGENTS.md lo prohíbe).
export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={BASENAME}>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
