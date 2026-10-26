import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { OrderDetail } from "../api/types";
import { useMoneyMutation } from "../hooks/useMoneyMutation";
import { useOrderCatalog } from "../hooks/useOrders";
import { cx } from "../lib/cx";
import { formatCop } from "../lib/format";
import { Button } from "../ui/Button";
import { FormAlert } from "../ui/FormAlert";
import { CashFields } from "./CashFields";
import {
  initialDraft,
  remainingCents,
  takesReference,
  toggleSplit,
  toRequest,
  usesCash,
  usesCredit,
  type CheckoutDraft,
} from "./checkoutDraft";
import { CreditFields } from "./CreditFields";
import styles from "./OrderDetail.module.css";
import { PayMethods, type MethodOption } from "./PayMethods";
import { SingleReference } from "./SingleReference";
import { SplitParts } from "./SplitParts";

interface CheckoutFormProps {
  order: OrderDetail;
}

const CREDIT_OPTION: MethodOption = { value: "fiado", label: "Fiado" };

/** Las formas de pago de la sede (y Fiado si hay cliente) y cuántas partes acepta el servidor. */
function useCheckoutOptions(order: OrderDetail): { methods: MethodOption[]; maxParts: number } {
  const catalog = useOrderCatalog();
  const enabled = catalog.data?.methods ?? [];
  const methods = order.credit === null ? enabled : [...enabled, CREDIT_OPTION];
  return { methods, maxParts: catalog.data?.max_parts ?? 1 };
}

/** El cobro: una forma de pago o dividido en hasta 3 partes, con vueltas y fiado. Un solo envío. */
export function CheckoutForm({ order }: CheckoutFormProps) {
  const { methods, maxParts } = useCheckoutOptions(order);
  const [draft, setDraft] = useState<CheckoutDraft | null>(null);
  const current = draft ?? initialDraft(methods[0]?.value ?? "");
  const charge = useMoneyMutation(() =>
    api.post("/api/v1/orders/{public_id}/checkout/", toRequest(current), { public_id: order.id }),
  );
  const errors = formErrors(charge.error);
  const remaining = remainingCents(current, order.total);
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    charge.submit(undefined);
  };
  if (methods.length === 0) return null;
  return (
    <form className={cx(styles.section, styles.checkout)} onSubmit={submit} aria-label="Cobrar la comanda">
      <h3 className={styles.subhead}>Forma de pago</h3>
      {current.split ? (
        <SplitParts
          draft={current}
          methods={methods}
          maxParts={maxParts}
          total={order.total}
          error={errors.fields.parts}
          onChange={setDraft}
        />
      ) : (
        <PayMethods draft={current} methods={methods} error={errors.fields.parts} onChange={setDraft} />
      )}
      {usesCash(current) && (
        <CashFields draft={current} total={order.total} error={errors.fields.received} onChange={setDraft} />
      )}
      {takesReference(current) && <SingleReference draft={current} onChange={setDraft} />}
      {usesCredit(current) && order.credit && (
        <CreditFields
          draft={current}
          credit={order.credit}
          branch={order.branch}
          error={errors.fields.due_date}
          onChange={setDraft}
        />
      )}
      <FormAlert message={errors.detail} />
      <Button
        type="submit"
        block
        className={styles.charge}
        disabled={charge.isPending || (remaining !== null && remaining !== 0)}
      >
        {charge.isPending ? "Cobrando…" : `Cobrar ${formatCop(order.total)}`}
      </Button>
      <Button
        kind="text"
        className={styles.center}
        onClick={() => {
          setDraft(toggleSplit(current));
        }}
      >
        {current.split ? "Pagar con una sola forma" : "Dividir el pago"}
      </Button>
    </form>
  );
}
