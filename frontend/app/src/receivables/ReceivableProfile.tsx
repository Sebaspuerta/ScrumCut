import { useId } from "react";

import type { ReceivableDetail } from "../api/types";
import { formatCop } from "../lib/format";
import { Notice } from "../ui/Notice";
import { PaymentHistory } from "./PaymentHistory";
import { PayReceivableForm } from "./PayReceivableForm";
import { ReceivableHead } from "./ReceivableHead";
import styles from "./Receivables.module.css";

interface ReceivableProfileProps {
  receivable: ReceivableDetail;
  onPaid: (message: string) => void;
  onClose: () => void;
}

/** El fiado elegido: saldo, total y abonado; el abono si el rol puede y está en su sede; y los abonos anteriores. */
export function ReceivableProfile({ receivable, onPaid, onClose }: ReceivableProfileProps) {
  const titleId = useId();
  return (
    <section className={styles.panel} aria-labelledby={titleId}>
      <ReceivableHead receivable={receivable} titleId={titleId} onClose={onClose} />
      <div className={styles.amount}>
        <span className={styles.eyebrow}>Saldo pendiente</span>
        <strong>{formatCop(receivable.balance)}</strong>
        <small className={styles.muted}>
          Total {formatCop(receivable.total)} · abonado {formatCop(receivable.paid)}
        </small>
      </div>
      {receivable.needs_branch && (
        <Notice>
          Para abonar, elige la sede {receivable.branch} en la barra superior: un fiado solo se abona en su sede.
        </Notice>
      )}
      {receivable.actions.pay && <PayReceivableForm key={receivable.balance} receivable={receivable} onPaid={onPaid} />}
      <PaymentHistory payments={receivable.payments} />
    </section>
  );
}
