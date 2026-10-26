import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { ClientChoice } from "../api/types";
import { useMoneyMutation } from "../hooks/useMoneyMutation";
import { useOrderCatalog } from "../hooks/useOrders";
import { StatusMessage } from "../frame/StatusMessage";
import { Button } from "../ui/Button";
import form from "../ui/Form.module.css";
import { FormAlert } from "../ui/FormAlert";
import { FormDialog } from "../ui/FormDialog";
import { ClientPicker } from "./ClientPicker";
import { toNewLine, type LineDraft } from "./lineDraft";
import { NewOrderLines } from "./NewOrderLines";
import { OrderBarberField } from "./OrderBarberField";
import styles from "./OrderDetail.module.css";

interface NewOrderDialogProps {
  onClose: () => void;
  onCreated: (id: string) => void;
}

/** Nueva comanda en la sede activa: cliente (opcional), barbero y sus líneas al precio vigente de la sede. */
export function NewOrderDialog({ onClose, onCreated }: NewOrderDialogProps) {
  const catalog = useOrderCatalog();
  const [client, setClient] = useState<ClientChoice | null>(null);
  const [barber, setBarber] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([]);
  const create = useMoneyMutation(() =>
    api.post("/api/v1/orders/create/", {
      client: client?.id ?? null,
      barber: barber || null,
      lines: lines.map(toNewLine),
    }),
  );
  const errors = formErrors(create.error);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    create.submit(undefined, (order) => {
      onCreated(order.id);
    });
  };
  return (
    <FormDialog
      title="Nueva comanda"
      subtitle={catalog.data?.branch ? `Sede ${catalog.data.branch}` : undefined}
      onClose={onClose}
    >
      <div className={styles.dialogBody}>
        <h3 className={styles.subhead}>Cliente</h3>
        <p className={styles.muted}>
          {client
            ? `${client.name}${client.phone ? ` · ${client.phone}` : ""}`
            : "Sin cliente: de mostrador, no puede quedar como fiado."}
        </p>
        <ClientPicker selected={client} onPick={setClient} />
        {client && (
          <Button
            kind="text"
            onClick={() => {
              setClient(null);
            }}
          >
            Dejar sin cliente
          </Button>
        )}
        <FormAlert message={errors.fields.client ?? null} />
        {catalog.isPending && <StatusMessage kind="loading">Cargando servicios y productos…</StatusMessage>}
        {catalog.isError && <StatusMessage kind="error">No pudimos cargar los servicios y productos.</StatusMessage>}
        {catalog.data && (
          <form className={form.form} onSubmit={submit} aria-label="Abrir la comanda">
            <OrderBarberField catalog={catalog.data} value={barber} error={errors.fields.barber} onChange={setBarber} />
            <NewOrderLines catalog={catalog.data} lines={lines} error={errors.fields.lines} onChange={setLines} />
            <FormAlert message={errors.detail} />
            <div className={form.actions}>
              <Button kind="secondary" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={create.isPending || catalog.data.needs_branch}>
                Abrir comanda
              </Button>
            </div>
          </form>
        )}
      </div>
    </FormDialog>
  );
}
