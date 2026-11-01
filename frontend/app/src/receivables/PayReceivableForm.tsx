import { useState, type SubmitEvent } from "react";

import { api } from "../api/client";
import { formErrors } from "../api/errors";
import type { ReceivableDetail, ReceivablePaymentRequest } from "../api/types";
import { useWriteMutation } from "../hooks/useWriteMutation";
import { MAX_LENGTH } from "../lib/fieldLimits";
import { formatCop } from "../lib/format";
import { isZeroAmount } from "../lib/money";
import { CASH_METHOD } from "../lib/paymentMethods";
import { ReferenceInput } from "../orders/ReferenceInput";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import { FormAlert } from "../ui/FormAlert";
import input from "../ui/Input.module.css";
import { PayMethods } from "../ui/PayMethods";
import { AmountField } from "./AmountField";
import { ConfirmPaymentDialog } from "./ConfirmPaymentDialog";
import { initialPayment, preview, toRequest } from "./paymentDraft";
import { PAYMENT_ANCHOR } from "./receivableParams";
import styles from "./Receivables.module.css";

interface PayReceivableFormProps {
  receivable: ReceivableDetail;
  onPaid: (message: string) => void;
}

function paidMessage(amount: string, updated: ReceivableDetail): string {
  const paid = `Abono de ${formatCop(amount)} registrado`;
  return isZeroAmount(updated.balance)
    ? `${paid}: el fiado quedó pagado.`
    : `${paid}. Saldo: ${formatCop(updated.balance)}.`;
}

/** El abono, parcial o total: monto con «Pagar todo», forma de pago con su referencia, nota opcional y confirmación antes de
 * enviarlo. Un doble clic envía una sola petición y el servidor rechaza un segundo envío del mismo abono. */
export function PayReceivableForm({ receivable, onPaid }: PayReceivableFormProps) {
  const [draft, setDraft] = useState(() => initialPayment(receivable));
  const [confirming, setConfirming] = useState(false);
  const pay = useWriteMutation((request: ReceivablePaymentRequest) =>
    api.post("/api/v1/receivables/{public_id}/pay/", request, { public_id: receivable.id }),
  );
  const errors = formErrors(pay.error);
  const check = preview(draft, receivable.balance);
  const method = receivable.methods.find((option) => option.value === draft.method)?.label ?? draft.method;
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    if (check.valid) setConfirming(true);
  };
  const confirm = () => {
    pay.submit(toRequest(draft, receivable.balance), (updated) => {
      setConfirming(false);
      setDraft(initialPayment(receivable));
      onPaid(paidMessage(draft.amount, updated));
    });
  };
  const cash = draft.method === CASH_METHOD;
  return (
    <form id={PAYMENT_ANCHOR} className={styles.form} onSubmit={submit} aria-label="Registrar abono">
      <AmountField draft={draft} balance={receivable.balance} error={errors.fields.amount} onChange={setDraft} />
      <p className={styles.preview} aria-live="polite">
        {check.text}
      </p>
      <PayMethods
        value={draft.method}
        methods={receivable.methods}
        error={errors.fields.method}
        onChange={(value) => {
          setDraft({ ...draft, method: value });
        }}
      />
      <p className={styles.muted}>
        {cash
          ? `El efectivo entra a la caja abierta de ${receivable.branch}.`
          : "No entra a la caja física: queda en «otros medios» del cierre."}
      </p>
      {!cash && (
        <Field label="Referencia del pago" error={errors.fields.reference}>
          {(control) => (
            <ReferenceInput
              {...control}
              value={draft.reference}
              onChange={(reference) => {
                setDraft({ ...draft, reference });
              }}
            />
          )}
        </Field>
      )}
      <Field label="Nota (opcional)" error={errors.fields.note}>
        {(control) => (
          <input
            {...control}
            className={input.input}
            placeholder="Ej.: abonó al recoger a su hijo"
            maxLength={MAX_LENGTH.ReceivablePaymentRequest.note}
            value={draft.note}
            onChange={(event) => {
              setDraft({ ...draft, note: event.target.value });
            }}
          />
        )}
      </Field>
      {!confirming && <FormAlert message={errors.detail} />}
      <Button type="submit" block className={styles.submit} disabled={!check.valid || pay.isPending}>
        {check.valid ? `Registrar abono de ${formatCop(draft.amount)}` : "Registrar abono"}
      </Button>
      {confirming && (
        <ConfirmPaymentDialog
          summary={`Abono de ${formatCop(draft.amount)} por ${method} a ${receivable.client.name}.`}
          after={check.text}
          busy={pay.isPending}
          error={errors.detail}
          onCancel={() => {
            setConfirming(false);
          }}
          onConfirm={confirm}
        />
      )}
    </form>
  );
}
