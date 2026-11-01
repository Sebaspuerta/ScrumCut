import { useId } from "react";

import type { ClientDetail } from "../api/types";
import { ClientDebt } from "./ClientDebt";
import { ClientFacts } from "./ClientFacts";
import { ClientHead } from "./ClientHead";
import { ClientLevel } from "./ClientLevel";
import { ClientReceivables } from "./ClientReceivables";
import styles from "./Clients.module.css";
import { ClientVisits } from "./ClientVisits";
import { NewOrderForClient } from "./NewOrderForClient";

interface ClientProfileProps {
  client: ClientDetail;
  branch: string;
  onEdit: () => void;
  onClose: () => void;
}

/** La ficha: la identidad es de la barbería; nivel, historial y fiados, de la sede. Sin historial aquí, solo la
 * identidad. */
export function ClientProfile({ client, branch, onEdit, onClose }: ClientProfileProps) {
  const titleId = useId();
  const activity = client.activity;
  return (
    <section className={styles.panel} aria-labelledby={titleId}>
      <ClientHead client={client} titleId={titleId} onEdit={onEdit} onClose={onClose} />
      {activity ? (
        <>
          <ClientLevel activity={activity} branch={branch} />
          <ClientFacts activity={activity} />
          <ClientDebt activity={activity} branch={branch} />
        </>
      ) : (
        <p className={styles.muted}>Sin historial en esta sede. El nivel, las visitas y los fiados son de cada sede.</p>
      )}
      {client.notes && (
        <>
          <h3 className={styles.subhead}>Preferencias</h3>
          <p className={styles.notes}>{client.notes}</p>
        </>
      )}
      {activity && <ClientVisits visits={activity.last_visits} branch={branch} />}
      {client.receivables && <ClientReceivables receivables={client.receivables} branch={branch} />}
      {client.actions.new_order && <NewOrderForClient client={client} />}
      <p className={styles.note}>
        El historial, el nivel y los fiados son de esta sede. Otras sedes solo comparten el nombre y el contacto.
      </p>
    </section>
  );
}
