import type { OrderCatalog } from "../api/types";
import { formatCop } from "../lib/format";
import { itemValue, PRODUCT, SERVICE } from "./lineDraft";

interface ItemOptionsProps {
  catalog: OrderCatalog;
}

/** Las opciones del selector de ítems: servicios y productos con el precio (y el stock) de la sede. */
export function ItemOptions({ catalog }: ItemOptionsProps) {
  return (
    <>
      <option value="">Elige un servicio o un producto</option>
      <optgroup label="Servicios">
        {catalog.services.map((service) => (
          <option key={service.id} value={itemValue(SERVICE, service.id)}>
            {service.name} · {formatCop(service.price)}
          </option>
        ))}
      </optgroup>
      <optgroup label="Productos">
        {catalog.products.map((product) => (
          <option key={product.id} value={itemValue(PRODUCT, product.id)}>
            {product.name} · {formatCop(product.price)} · {product.stock} en stock
          </option>
        ))}
      </optgroup>
    </>
  );
}
