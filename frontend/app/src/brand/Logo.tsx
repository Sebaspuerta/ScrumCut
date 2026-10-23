import { BrandMark } from "./BrandMark";
import styles from "./Logo.module.css";

interface LogoProps {
  /** Solo el símbolo compacto, sin el texto (la barra superior en el celular). */
  compact?: boolean;
  /** En pantallas angostas deja solo el símbolo (la barra superior). */
  collapsible?: boolean;
}

export function Logo({ compact = false, collapsible = false }: LogoProps) {
  const words = [styles.words, collapsible ? styles.collapsible : ""].join(" ");
  return (
    <div className={styles.logo}>
      <BrandMark variant={compact ? "compact" : "ring"} className={styles.mark} />
      <div className={compact ? "visually-hidden" : words}>
        <b className={styles.name}>SCRUMCUT</b>
        <small className={styles.tagline}>Gestión para barberías</small>
      </div>
    </div>
  );
}
