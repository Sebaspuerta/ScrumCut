import type { RouteObject } from "react-router";

import { CashPage } from "./cash/CashPage";
import { DashboardPage } from "./dashboard/DashboardPage";
import { AppFrame } from "./frame/AppFrame";
import { CASH_PATH, ORDERS_PATH } from "./lib/appRoutes";
import { OrdersPage } from "./orders/OrdersPage";
import { NotFoundPage } from "./pages/NotFoundPage";

/** Django entrega la página en /app/ y en cualquier subruta; desde ahí elige la pantalla el enrutador. */
export const BASENAME = "/app";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppFrame />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: ORDERS_PATH, element: <OrdersPage /> },
      { path: CASH_PATH, element: <CashPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
