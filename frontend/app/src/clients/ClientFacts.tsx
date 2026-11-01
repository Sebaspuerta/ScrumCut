import type { ClientActivity } from "../api/types";
import { formatCop } from "../lib/format";
import styles from "./Clients.module.css";

interface ClientFactsProps {
  activity: ClientActivity;
}

const EMPTY = "—";

/** Ticket promedio, gasto en la sede, barbero habitual y lo que más pide. */
export function ClientFacts({ activity }: ClientFactsProps) {
  const barber = activity.barber;
  const facts = [
    { label: "Ticket promedio", value: formatCop(activity.ticket) },
    { label: "Gasto total en la sede", value: formatCop(activity.spent) },
    {
      label: "Barbero habitual",
      value: barber ? `${barber.name} · ${String(barber.visits)} de ${String(activity.visits)}` : EMPTY,
    },
    { label: "Lo que más pide", value: activity.favorite ?? EMPTY },
  ];
  return (
    <dl className={styles.facts}>
      {facts.map((fact) => (
        <div key={fact.label}>
          <dt>{fact.label}</dt>
          <dd>{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}
