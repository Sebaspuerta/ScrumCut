import styles from "./FormAlert.module.css";

interface FormAlertProps {
  message: string | null;
}

/** El error general de un formulario: se anuncia al aparecer. Sin error no ocupa lugar. */
export function FormAlert({ message }: FormAlertProps) {
  if (message === null) return null;
  return (
    <p className={styles.alert} role="alert">
      {message}
    </p>
  );
}
