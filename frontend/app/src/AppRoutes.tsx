import { useRoutes } from "react-router";

import { routes } from "./routes";

export function AppRoutes() {
  return useRoutes(routes);
}
