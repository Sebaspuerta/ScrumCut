// Símbolo de ScrumCut (docs/diseno/marca): navaja abierta, con doble aro o compacta. Sin color fijo:
// toma currentColor, así funciona en claro y en oscuro.

const SHAPES = {
  ring: {
    scale: 1.1,
    blade: "M9,-4.6 C20,-5.3 38,-5.1 58,-2.5 Q62.4,0 58,2.5 C38,5.1 20,5.3 9,4.6 Q7.4,0 9,-4.6 Z",
    handle: [
      "M3,-3.4 L52,-6 Q57,-6.2 57.4,-1.6 L57.4,3.6 L15,3.0 L4.4,2.4 Z",
      "M15,4.0 L57.4,4.6 Q57.2,8.8 52,8.8 L14,7.6 Q9.2,7.3 7,5.2 Z",
      "M4,-3.4 L-3.5,-3.1 Q-9,-2.7 -11,0.6 Q-12.3,3.4 -10.2,4.7 Q-9.4,2.3 -5.8,1.9 L4.6,1.6 Z",
    ],
  },
  compact: {
    scale: 1.3,
    blade: "M9,-5 C20,-5.8 38,-5.6 58,-3 Q62.6,0 58,3 C38,5.6 20,5.8 9,5 Q7.2,0 9,-5 Z",
    handle: [
      "M3,-3.8 L52,-6.4 Q57.4,-6.6 57.8,-1.6 L57.8,5 Q57.6,9.2 52,9.2 L14,8 Q8,7.6 4.6,3.6 Z",
      "M4,-3.8 L-3.5,-3.5 Q-9.4,-3 -11.4,0.6 Q-12.8,3.8 -10.4,5 Q-9.4,2.6 -5.6,2.2 L4.6,1.8 Z",
    ],
  },
} as const;

interface BrandMarkProps {
  variant: keyof typeof SHAPES;
  className?: string | undefined;
}

/** Decorativo: el nombre de la marca va siempre en texto al lado. */
export function BrandMark({ variant, className }: BrandMarkProps) {
  const shape = SHAPES[variant];
  const placement = `translate(60 61) scale(${String(shape.scale)}) translate(-66 -58) rotate(-14 60 60) translate(93 47)`;
  return (
    <svg className={className} viewBox="0 0 120 120" fill="currentColor" aria-hidden="true" focusable="false">
      {variant === "ring" && (
        <>
          <circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" strokeWidth="1.3" />
          <circle cx="60" cy="60" r="52" fill="none" stroke="currentColor" strokeWidth="0.5" />
        </>
      )}
      <g transform={placement}>
        <path transform="rotate(150)" d={shape.blade} />
        <g transform="rotate(186) scale(1 -1)">
          {shape.handle.map((path) => (
            <path key={path} d={path} />
          ))}
        </g>
      </g>
    </svg>
  );
}
