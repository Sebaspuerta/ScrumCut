import type { ProductDetail, ProductList } from "../api/types";
import { useProduct } from "../hooks/useInventory";
import { PRODUCT_PARAM } from "../lib/appRoutes";
import { withParam } from "../lib/searchParams";
import { AdjustmentDialog } from "./AdjustmentDialog";
import { CategoriesDialog } from "./CategoriesDialog";
import { EntryDialog } from "./EntryDialog";
import {
  CATEGORIES_PARAM,
  EDIT_PARAM,
  HISTORY_PARAM,
  moveOf,
  MOVE_PARAM,
  NEW_PARAM,
  type Move,
} from "./inventoryParams";
import { ProductFormDialog } from "./ProductFormDialog";
import { TransferDialog } from "./TransferDialog";

interface InventoryDialogsProps {
  list: ProductList | undefined;
  selected: string | null;
  /** La sede activa; en «todas», null. */
  branch: string | null;
  permissions: string[];
  params: URLSearchParams;
  onParams: (params: URLSearchParams) => void;
}

const MOVE_DIALOGS: Record<Move, typeof EntryDialog> = {
  entrada: EntryDialog,
  ajuste: AdjustmentDialog,
  traslado: TransferDialog,
};

/** Nuevo producto (?nuevo=1), editarlo (?editar=1), categorías (?categorias=1) y mover su stock (?mover=…): todo en
 * la URL. Cada diálogo sale solo si el servidor permite la acción. */
export function InventoryDialogs({ list, selected, branch, permissions, params, onParams }: InventoryDialogsProps) {
  const open = params.get(EDIT_PARAM) !== null || params.get(MOVE_PARAM) !== null;
  const product = useProduct(open ? selected : null, params.get(HISTORY_PARAM) ?? "1").data;
  const close = (key: string) => () => {
    onParams(withParam(params, key, null));
  };
  const saved = (next: ProductDetail) => {
    onParams(withParam(withParam(withParam(params, NEW_PARAM, null), EDIT_PARAM, null), PRODUCT_PARAM, next.id));
  };
  const move = moveOf(params);
  if (params.get(NEW_PARAM) !== null && list && permissions.includes("inventario.crear")) {
    const options = { categories: list.categories, types: list.types, branch };
    return <ProductFormDialog product={null} {...options} onClose={close(NEW_PARAM)} onSaved={saved} />;
  }
  if (params.get(CATEGORIES_PARAM) !== null) {
    return <CategoriesDialog permissions={permissions} onClose={close(CATEGORIES_PARAM)} />;
  }
  if (product?.actions.edit && params.get(EDIT_PARAM) !== null && list) {
    const options = { categories: list.categories, types: list.types, branch };
    return <ProductFormDialog product={product} {...options} onClose={close(EDIT_PARAM)} onSaved={saved} />;
  }
  if (product?.actions.adjust && move) {
    const MoveDialog = MOVE_DIALOGS[move];
    return <MoveDialog product={product} onClose={close(MOVE_PARAM)} />;
  }
  return null;
}
