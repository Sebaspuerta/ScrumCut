import { useNavigate } from "react-router";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { ClientDetail } from "../api/types";
import { useWriteMutation } from "../hooks/useWriteMutation";
import { orderPath } from "../lib/appRoutes";
import { Button } from "../ui/Button";
import { FormAlert } from "../ui/FormAlert";
import styles from "./Clients.module.css";

interface NewOrderForClientProps {
  client: ClientDetail;
}

const firstName = (name: string) => name.split(" ")[0] ?? name;

/** «Nueva comanda para Laura»: la abre en la sede actual con el cliente y lleva a ella. */
export function NewOrderForClient({ client }: NewOrderForClientProps) {
  const navigate = useNavigate();
  const create = useWriteMutation(() => api.post("/api/v1/orders/create/", { client: client.id }));
  return (
    <>
      <Button
        block
        className={styles.newOrder}
        disabled={create.isPending}
        onClick={() => {
          create.submit(undefined, (order) => {
            void navigate(orderPath(order.id));
          });
        }}
      >
        Nueva comanda para {firstName(client.name)}
      </Button>
      <FormAlert message={formErrors(create.error).detail} />
    </>
  );
}
