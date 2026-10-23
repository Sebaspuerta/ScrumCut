import { Link } from "react-router";

import styles from "./NotFoundPage.module.css";

export function NotFoundPage() {
  return (
    <section className={styles.page}>
      <h1>Esta página no existe</h1>
      <Link to="/">Volver al tablero</Link>
    </section>
  );
}
