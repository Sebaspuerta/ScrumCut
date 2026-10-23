import type { RouteObject } from "react-router";

import { DashboardPage } from "./dashboard/DashboardPage";
import { AppFrame } from "./frame/AppFrame";
import { NotFoundPage } from "./pages/NotFoundPage";

/** Django entrega la página en /app/ y en cualquier subruta; desde ahí elige la pantalla el enrutador. */
export const BASENAME = "/app";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppFrame />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
