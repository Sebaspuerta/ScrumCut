import { signedCop } from "../lib/format";
import { isNegativeAmount, isZeroAmount } from "../lib/money";
import { Change } from "./Change";

interface DifferenceProps {
  /** Contado − esperado, en texto decimal. */
  value: string;
  /** Agrega «sobrante» o «faltante» (el arqueo antes de cerrar). */
  explained?: boolean;
}

/** La diferencia de un arqueo: «Cuadrada», o el monto con signo y flecha. Sin rojos. */
export function Difference({ value, explained = false }: DifferenceProps) {
  if (isZeroAmount(value)) return <span>Cuadrada</span>;
  const negative = isNegativeAmount(value);
  const note = explained ? (negative ? " · faltante" : " · sobrante") : "";
  return (
    <Change direction={negative ? "down" : "up"}>
      {signedCop(value)}
      {note}
    </Change>
  );
}
