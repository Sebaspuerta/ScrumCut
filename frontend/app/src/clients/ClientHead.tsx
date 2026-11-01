import { X } from "lucide-react";

import type { ClientDetail } from "../api/types";
import { useTimeZone } from "../hooks/useMe";
import { monthLabel, zonedDate } from "../lib/format";
import { Button } from "../ui/Button";
import styles from "./Clients.module.css";

interface ClientHeadProps {
  client: ClientDetail;
  titleId: string;
  onEdit: () => void;
  onClose: () => void;
}

/** Iniciales, nombre, celular enmascarado y «cliente desde»; Editar si el rol puede, y cerrar la ficha. */
export function ClientHead({ client, titleId, onEdit, onClose }: ClientHeadProps) {
  const timeZone = useTimeZone();
  const since = monthLabel(zonedDate(client.since, timeZone)).toLowerCase();
  return (
    <div className={styles.head}>
      <span className={styles.avatar} aria-hidden="true">
        {client.initials}
      </span>
      <div className={styles.identity}>
        <h2 id={titleId} className={styles.name}>
          {client.name}
        </h2>
        <p className={styles.muted}>
          {client.phone ?? "Sin celular"} · cliente desde {since}
        </p>
      </div>
      <div className={styles.headActions}>
        {client.actions.edit && (
          <Button kind="secondary" onClick={onEdit}>
            Editar
          </Button>
        )}
        <button type="button" className={styles.close} aria-label="Cerrar la ficha" onClick={onClose}>
          <X size={18} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
