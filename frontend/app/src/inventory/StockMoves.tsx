import { ArrowLeftRight, Minus, Plus } from "lucide-react";

import type { ProductDetail } from "../api/types";
import { StatusMessage } from "../frame/StatusMessage";
import { Button } from "../ui/Button";
import type { Move } from "./inventoryParams";
import styles from "./Inventory.module.css";

interface StockMovesProps {
  product: ProductDetail;
  onMove: (move: Move) => void;
}

/** Entrada, ajuste y traslado: arriba del panel y a lo ancho, para registrarlos a un toque desde el celular. */
export function StockMoves({ product, onMove }: StockMovesProps) {
  if (product.needs_branch) {
    return <StatusMessage kind="empty">Elige una sede en la barra superior para mover el stock.</StatusMessage>;
  }
  if (!product.actions.adjust) return null;
  return (
    <div className={styles.moves} role="group" aria-label="Mover stock">
      <Button
        onClick={() => {
          onMove("entrada");
        }}
      >
        <Plus size={16} aria-hidden="true" />
        Entrada
      </Button>
      <Button
        kind="secondary"
        onClick={() => {
          onMove("ajuste");
        }}
      >
        <Minus size={16} aria-hidden="true" />
        Ajuste
      </Button>
      {product.destinations.length > 0 && (
        <Button
          kind="secondary"
          onClick={() => {
            onMove("traslado");
          }}
        >
          <ArrowLeftRight size={16} aria-hidden="true" />
          Traslado
        </Button>
      )}
    </div>
  );
}
