import { X } from "lucide-react";
import { useId } from "react";

import { useEscape } from "../hooks/useEscape";
import { Pill } from "../ui/Pill";
import styles from "./AssistantPanel.module.css";

interface AssistantPanelProps {
  onClose: () => void;
}

/** El asistente va en la interfaz pero sin funcionalidad hasta que el backend esté completo (AGENTS.md). */
export function AssistantPanel({ onClose }: AssistantPanelProps) {
  const titleId = useId();
  const fieldId = useId();
  useEscape(true, onClose);
  return (
    <section className={styles.assistant} aria-labelledby={titleId}>
      <div className={styles.head}>
        <div>
          <h2 id={titleId}>Asistente</h2>
          <p>Responderá con los datos de tu barbería</p>
        </div>
        <button type="button" className={styles.close} aria-label="Cerrar el asistente" onClick={onClose}>
          <X size={20} aria-hidden="true" />
        </button>
      </div>
      <div className={styles.chat}>
        <Pill>Disponible pronto</Pill>
        <p className={styles.bot}>El asistente estará disponible pronto.</p>
      </div>
      <div className={styles.composer}>
        <label htmlFor={fieldId} className="visually-hidden">
          Pregunta para el asistente
        </label>
        <input id={fieldId} placeholder="Escribe tu pregunta" disabled />
      </div>
    </section>
  );
}
