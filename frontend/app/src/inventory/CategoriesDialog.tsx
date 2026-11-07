import { LoadError } from "../frame/LoadError";
import { StatusMessage } from "../frame/StatusMessage";
import { useCategories } from "../hooks/useInventory";
import { FormDialog } from "../ui/FormDialog";
import { CategoryRow } from "./CategoryRow";
import styles from "./Inventory.module.css";
import { NewCategoryForm } from "./NewCategoryForm";

interface CategoriesDialogProps {
  permissions: string[];
  onClose: () => void;
}

/** Las categorías de productos de la barbería: crear (inventario.crear), renombrar (editar) y borrar (eliminar). */
export function CategoriesDialog({ permissions, onClose }: CategoriesDialogProps) {
  const categories = useCategories(true);
  const results = categories.data?.results;
  return (
    <FormDialog title="Categorías" subtitle="Son de la barbería: las ven todas las sedes." onClose={onClose}>
      {permissions.includes("inventario.crear") && <NewCategoryForm />}
      {categories.isPending && <StatusMessage kind="loading">Cargando las categorías…</StatusMessage>}
      {categories.isError && (
        <LoadError error={categories.error} onRetry={() => void categories.refetch()}>
          No pudimos cargar las categorías.
        </LoadError>
      )}
      {results?.length === 0 && <p className={styles.muted}>Todavía no hay categorías.</p>}
      {results && results.length > 0 && (
        <ul className={styles.lines}>
          {results.map((category) => (
            <CategoryRow
              key={`${category.id}-${category.name}`}
              category={category}
              canRename={permissions.includes("inventario.editar")}
              canDelete={permissions.includes("inventario.eliminar")}
            />
          ))}
        </ul>
      )}
    </FormDialog>
  );
}
