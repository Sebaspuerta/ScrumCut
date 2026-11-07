// Las pantallas de la app de React (dentro de /app/). Las de Django que aún no migran están en djangoRoutes.ts.
export const ORDERS_PATH = "/comandas";
export const CASH_PATH = "/caja";
export const CLIENTS_PATH = "/clientes";
export const RECEIVABLES_PATH = "/fiados";
export const INVENTORY_PATH = "/inventario";
// ?registrar=gasto abre el registro de un movimiento en Caja ("+ Nuevo › Registrar gasto" en navigation.py).
export const REGISTER_PARAM = "registrar";
export const COUNT_ANCHOR = "arqueo";
// Lo que abre el panel de cada pantalla: la comanda, el cliente o el fiado elegido.
export const ORDER_PARAM = "comanda";
export const CLIENT_PARAM = "cliente";
export const RECEIVABLE_PARAM = "fiado";
export const PRODUCT_PARAM = "producto";

const opening = (path: string, key: string, id: string) => `${path}?${new URLSearchParams({ [key]: id }).toString()}`;

/** La comanda abierta en su panel de Comandas. */
export const orderPath = (id: string) => opening(ORDERS_PATH, ORDER_PARAM, id);
/** La ficha del cliente en Clientes. */
export const clientPath = (id: string) => opening(CLIENTS_PATH, CLIENT_PARAM, id);
/** El fiado abierto en Fiados, con su abono. */
export const receivablePath = (id: string) => opening(RECEIVABLES_PATH, RECEIVABLE_PARAM, id);
/** El producto abierto en su panel de Inventario. */
export const productPath = (id: string) => opening(INVENTORY_PATH, PRODUCT_PARAM, id);
