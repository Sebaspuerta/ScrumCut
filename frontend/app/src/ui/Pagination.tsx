import { ChevronLeft, ChevronRight } from "lucide-react";

import styles from "./Pagination.module.css";

interface PaginationProps {
  page: number;
  pages: number;
  count: number;
  pageSize: number;
  label: string;
  onPage: (page: number) => void;
}

/** «1–20 de 312» y los botones de la página anterior y la siguiente. */
export function Pagination({ page, pages, count, pageSize, label, onPage }: PaginationProps) {
  if (pages <= 1) return null;
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, count);
  return (
    <nav className={styles.pagination} aria-label={label}>
      <span>
        {first}–{last} de {count}
      </span>
      <div className={styles.buttons}>
        <button
          type="button"
          aria-label="Página anterior"
          disabled={page <= 1}
          onClick={() => {
            onPage(page - 1);
          }}
        >
          <ChevronLeft size={16} aria-hidden="true" />
        </button>
        <button
          type="button"
          aria-label="Página siguiente"
          disabled={page >= pages}
          onClick={() => {
            onPage(page + 1);
          }}
        >
          <ChevronRight size={16} aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
