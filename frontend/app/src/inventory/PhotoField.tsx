import { ImagePlus } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cx } from "../lib/cx";
import { Button, buttonClass } from "../ui/Button";
import { Field } from "../ui/Field";
import styles from "./Inventory.module.css";
import { ProductThumb } from "./ProductThumb";

interface PhotoFieldProps {
  /** La foto que ya tiene el producto (servida por la API); null si no tiene. */
  current: string | null;
  file: File | null;
  error: string | undefined;
  onChange: (file: File | null) => void;
}

const ACCEPTED = "image/png,image/jpeg,image/webp";

/** La vista previa se lee del archivo como data: (la CSP la permite en img-src); el servidor la valida igual. */
function usePreview(file: File | null): string | null {
  const [preview, setPreview] = useState<string | null>(null);
  useEffect(() => {
    if (file === null) return undefined;
    const reader = new FileReader();
    reader.onload = () => {
      setPreview(typeof reader.result === "string" ? reader.result : null);
    };
    reader.readAsDataURL(file);
    return () => {
      reader.abort();
    };
  }, [file]);
  return file === null ? null : preview;
}

/** La foto del producto: «Elegir foto» (o «Cambiar foto»), su vista previa y «Quitar» la elegida antes de guardar.
 * El campo de archivo real queda oculto a la vista pero no al teclado ni al lector de pantalla: la etiqueta con forma
 * de botón lo abre y muestra su foco. */
export function PhotoField({ current, file, error, onChange }: PhotoFieldProps) {
  const preview = usePreview(file);
  const inputRef = useRef<HTMLInputElement>(null);
  const clear = () => {
    if (inputRef.current) inputRef.current.value = "";
    onChange(null);
  };
  return (
    <Field label="Foto" error={error} hint="PNG, JPEG o WEBP de hasta 5 MB. Se guarda cuadrada.">
      {(control) => (
        <div className={styles.photoRow}>
          {preview ? (
            <img className={styles.preview} src={preview} alt="Vista previa de la foto" />
          ) : (
            <ProductThumb photo={current} large />
          )}
          <input
            {...control}
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            className={cx("visually-hidden", styles.fileInput)}
            onChange={(event) => {
              onChange(event.target.files?.[0] ?? null);
            }}
          />
          <label htmlFor={control.id} className={buttonClass("secondary")}>
            <ImagePlus size={16} aria-hidden="true" />
            {current || file ? "Cambiar foto" : "Elegir foto"}
          </label>
          {file && (
            <Button kind="text" onClick={clear}>
              Quitar
            </Button>
          )}
        </div>
      )}
    </Field>
  );
}
