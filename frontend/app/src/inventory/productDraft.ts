// El formulario de producto mientras se llena. Los montos viajan como el texto que escribió la persona y las
// existencias no se editan aquí: solo el stock inicial al crear, que entra en la sede activa.
import type { ProductCreateRequest, ProductDetail, ProductRequest, ProductType } from "../api/types";
import { asTyped } from "../lib/money";

export interface ProductDraft {
  name: string;
  category: string;
  product_type: ProductType;
  purchase_cost: string;
  sale_price: string;
  minimum_stock: string;
  expiration_date: string;
  supplier: string;
  initial_stock: string;
}

export type ProductTextField = Exclude<keyof ProductDraft, "product_type">;

const BLANK: ProductDraft = {
  name: "",
  category: "",
  product_type: "venta",
  purchase_cost: "",
  sale_price: "",
  minimum_stock: "",
  expiration_date: "",
  supplier: "",
  initial_stock: "",
};

/** Vacío para crear; al editar, lo que ya tiene el producto. */
export function initialProduct(product: ProductDetail | null): ProductDraft {
  if (product === null) return BLANK;
  return {
    ...BLANK,
    name: product.name,
    category: product.category?.id ?? "",
    product_type: product.product_type,
    purchase_cost: asTyped(product.purchase_cost),
    sale_price: asTyped(product.sale_price),
    minimum_stock: product.minimum_stock === null ? "" : String(product.minimum_stock),
    expiration_date: product.expiration_date ?? "",
    supplier: product.supplier,
  };
}

const wholeOrNull = (text: string) => (text === "" ? null : Number(text));

export function toProductRequest(draft: ProductDraft): ProductRequest {
  return {
    name: draft.name,
    category: draft.category || null,
    product_type: draft.product_type,
    purchase_cost: draft.purchase_cost,
    sale_price: draft.sale_price,
    minimum_stock: wholeOrNull(draft.minimum_stock),
    expiration_date: draft.expiration_date || null,
    supplier: draft.supplier,
  };
}

export function toCreateRequest(draft: ProductDraft): ProductCreateRequest {
  return { ...toProductRequest(draft), initial_stock: Number(draft.initial_stock || "0") };
}
