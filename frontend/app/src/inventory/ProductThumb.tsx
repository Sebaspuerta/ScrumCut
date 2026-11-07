import { Package } from "lucide-react";

import { cx } from "../lib/cx";
import styles from "./Inventory.module.css";

interface ProductThumbProps {
  photo: string | null;
  large?: boolean;
}

/** La foto del producto, servida por la API con la sesión; sin foto, el ícono del paquete. */
export function ProductThumb({ photo, large = false }: ProductThumbProps) {
  const className = cx(styles.thumb, large && styles.photo);
  if (photo === null) {
    return (
      <span className={className} aria-hidden="true">
        <Package size={large ? 28 : 18} />
      </span>
    );
  }
  return <img className={className} src={photo} alt="" loading="lazy" />;
}
