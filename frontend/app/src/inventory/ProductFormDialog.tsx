import { useRef, useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { Option, ProductDetail } from "../api/types";
import { useWriteMutation } from "../hooks/useWriteMutation";
import { Button } from "../ui/Button";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";
import { PhotoField } from "./PhotoField";
import { initialProduct, toCreateRequest, toProductRequest, type ProductDraft } from "./productDraft";
import { ProductFields } from "./ProductFields";
import { ProductNumbers } from "./ProductNumbers";

interface ProductFormDialogProps {
  product: ProductDetail | null;
  categories: Option[];
  types: Option[];
  branch: string | null;
  onClose: () => void;
  onSaved: (product: ProductDetail) => void;
}

function saveFields(id: string | null, draft: ProductDraft): Promise<ProductDetail> {
  if (id !== null)
    return api.post("/api/v1/inventory/products/{public_id}/edit/", toProductRequest(draft), { public_id: id });
  return api.post("/api/v1/inventory/products/create/", toCreateRequest(draft));
}

function uploadPhoto(id: string, photo: File): Promise<ProductDetail> {
  const body = new FormData();
  body.append("photo", photo);
  return api.upload("/api/v1/inventory/products/{public_id}/photo/upload/", body, { public_id: id });
}

/** Nuevo producto (con su stock inicial en la sede) o editar sus datos, con la foto y su vista previa. La foto se
 * sube después de guardar los datos; si la rechaza el servidor, el producto ya creado se edita, no se crea otro. */
export function ProductFormDialog({ product, categories, types, branch, onClose, onSaved }: ProductFormDialogProps) {
  const [draft, setDraft] = useState(() => initialProduct(product));
  const [photo, setPhoto] = useState<File | null>(null);
  const savedId = useRef(product?.id ?? null);
  const mutation = useWriteMutation(async () => {
    const saved = await saveFields(savedId.current, draft);
    savedId.current = saved.id;
    return photo ? uploadPhoto(saved.id, photo) : saved;
  });
  const errors = formErrors(mutation.error);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    mutation.submit(undefined, onSaved);
  };
  return (
    <FormDialog
      title={product ? `Editar ${product.name}` : "Nuevo producto"}
      subtitle="El catálogo es de la barbería; el stock y el precio propio son de cada sede."
      onClose={onClose}
    >
      <form className={form.form} onSubmit={submit} aria-label="Datos del producto">
        <ProductFields draft={draft} errors={errors} categories={categories} types={types} onChange={setDraft} />
        <ProductNumbers draft={draft} errors={errors} creating={product === null} branch={branch} onChange={setDraft} />
        <PhotoField current={product?.photo ?? null} file={photo} error={errors.fields.photo} onChange={setPhoto} />
        <FormAlert message={errors.detail} />
        <div className={form.actions}>
          <Button kind="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending || draft.name.trim() === ""}>
            {product ? "Guardar cambios" : "Crear producto"}
          </Button>
        </div>
      </form>
    </FormDialog>
  );
}
