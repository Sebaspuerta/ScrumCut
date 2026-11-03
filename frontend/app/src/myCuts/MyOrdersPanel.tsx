import type { MyCuts } from "../api/types";
import { longDate } from "../lib/format";
import { PAGE_PARAM, withFilter, withParam } from "../lib/searchParams";
import input from "../ui/Input.module.css";
import { Pagination } from "../ui/Pagination";
import { Panel } from "../ui/Panel";
import styles from "./MyCuts.module.css";
import { DAY_PARAM } from "./myCutsParams";
import { MyOrdersTable } from "./MyOrdersTable";

interface MyOrdersPanelProps {
  data: MyCuts;
  params: URLSearchParams;
  onParams: (params: URLSearchParams) => void;
}

/** Las comandas cerradas del día elegido (?fecha=), por páginas. */
export function MyOrdersPanel({ data, params, onParams }: MyOrdersPanelProps) {
  const dayInput = (
    <label className={styles.day}>
      <span>Día</span>
      <input
        className={input.input}
        type="date"
        value={params.get(DAY_PARAM) ?? data.day}
        onChange={(event) => {
          onParams(withFilter(params, DAY_PARAM, event.target.value));
        }}
      />
    </label>
  );
  return (
    <Panel title="Tus comandas cerradas" subtitle={longDate(data.day, true)} actions={dayInput}>
      <MyOrdersTable rows={data.results} />
      <Pagination
        page={data.page}
        pages={data.pages}
        count={data.count}
        pageSize={data.page_size}
        label="Páginas de tus comandas"
        onPage={(page) => {
          onParams(withParam(params, PAGE_PARAM, String(page)));
        }}
      />
    </Panel>
  );
}
