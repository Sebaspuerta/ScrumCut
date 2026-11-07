import { useSearchParams } from "react-router";

import { LoadError } from "../frame/LoadError";
import { StatusMessage } from "../frame/StatusMessage";
import { useMe } from "../hooks/useMe";
import { useMyCuts } from "../hooks/useMyCuts";
import { PageTitle } from "../ui/PageTitle";
import { myCutsQuery } from "./myCutsParams";
import { MyCutsSummary } from "./MyCutsSummary";
import { MyOrdersPanel } from "./MyOrdersPanel";

/** «Mis cortes»: lo del barbero de la sesión en la sede activa (hoy, el mes y sus comandas del día). El día va en la
 * URL; nunca el barbero. */
export function MyCutsPage() {
  const me = useMe();
  const [params, setParams] = useSearchParams();
  const cuts = useMyCuts(myCutsQuery(params));
  if (cuts.isPending) return <StatusMessage kind="loading">Cargando tus cortes…</StatusMessage>;
  if (cuts.isError) {
    return (
      <LoadError error={cuts.error} onRetry={() => void cuts.refetch()}>
        No pudimos cargar tus cortes.
      </LoadError>
    );
  }
  const data = cuts.data;
  if (data.barber === null) {
    return (
      <StatusMessage kind="empty">Tu usuario no está vinculado a un barbero: no hay cortes que mostrar.</StatusMessage>
    );
  }
  return (
    <>
      <PageTitle
        eyebrow="Operación"
        title="Mis cortes"
        subtitle={`${data.barber} · Sede ${me.data?.branch?.current_label ?? ""}`}
      />
      <MyCutsSummary label="Hoy" period={data.today} />
      <MyCutsSummary label="Este mes" period={data.month} />
      <MyOrdersPanel data={data} params={params} onParams={setParams} />
    </>
  );
}
