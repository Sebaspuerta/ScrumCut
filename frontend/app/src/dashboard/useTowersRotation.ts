// Giro de las torres 3D (portado de static/js/modules/sales-towers.js): arrastrar, botones y vista inicial.
// Solo se mueve cuando la persona lo pide. La transformación va por el CSSOM del nodo, no por un atributo
// style, así que cumple la CSP estricta.
import { useCallback, useEffect, useRef, useState, type PointerEvent, type RefObject } from "react";

export interface View {
  tilt: number;
  turn: number;
}

interface Fit {
  x: number;
  y: number;
  scale: number;
}

export const START: View = { tilt: 58, turn: -36 };
const TILT_RANGE = [20, 80] as const;
const FIT_MARGIN = 24;
const DRAG_TILT = 0.3;
const DRAG_TURN = 0.4;

const clamp = (value: number) => Math.max(TILT_RANGE[0], Math.min(TILT_RANGE[1], value));

const transformFor = (view: View, fit: Fit) =>
  `translate(${String(fit.x)}px, ${String(fit.y)}px) scale(${String(fit.scale)}) rotateX(${String(view.tilt)}deg) rotateZ(${String(view.turn)}deg)`;

function projectedBox(stage: HTMLElement) {
  const rects = [...stage.querySelectorAll("[data-bounds]")].map((node) => node.getBoundingClientRect());
  const left = Math.min(...rects.map((rect) => rect.left));
  const top = Math.min(...rects.map((rect) => rect.top));
  const right = Math.max(...rects.map((rect) => rect.right));
  const bottom = Math.max(...rects.map((rect) => rect.bottom));
  return { width: right - left || 1, height: bottom - top || 1, x: (left + right) / 2, y: (top + bottom) / 2 };
}

/** Escala y centra la vista inicial según el tamaño real del contenedor; se conserva al girar. */
function fitToStage(stage: HTMLElement, scene: HTMLElement): Fit {
  const area = stage.getBoundingClientRect();
  scene.style.transform = transformFor(START, { x: 0, y: 0, scale: 1 });
  const natural = projectedBox(stage);
  const widthRoom = (area.width - 2 * FIT_MARGIN) / natural.width;
  const scale = Math.min(1, widthRoom, (area.height - 2 * FIT_MARGIN) / natural.height);
  scene.style.transform = transformFor(START, { x: 0, y: 0, scale });
  const scaled = projectedBox(stage);
  return { x: area.left + area.width / 2 - scaled.x, y: area.top + area.height / 2 - scaled.y, scale };
}

function useDrag(view: View, setView: (view: View) => void) {
  const drag = useRef<{ x: number; y: number; from: View } | null>(null);
  return {
    onPointerDown: (event: PointerEvent<HTMLElement>) => {
      drag.current = { x: event.clientX, y: event.clientY, from: view };
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    onPointerMove: (event: PointerEvent<HTMLElement>) => {
      const start = drag.current;
      if (!start) return;
      setView({
        tilt: clamp(start.from.tilt - (event.clientY - start.y) * DRAG_TILT),
        turn: start.from.turn + (event.clientX - start.x) * DRAG_TURN,
      });
    },
    onPointerUp: () => {
      drag.current = null;
    },
  };
}

export function useTowersRotation(stageRef: RefObject<HTMLElement | null>, sceneRef: RefObject<HTMLElement | null>) {
  const [view, setView] = useState<View>(START);
  const fit = useRef<Fit>({ x: 0, y: 0, scale: 1 });
  const render = useCallback(
    (current: View) => {
      if (sceneRef.current) sceneRef.current.style.transform = transformFor(current, fit.current);
    },
    [sceneRef],
  );

  const current = useRef(view);
  useEffect(() => {
    current.current = view;
    render(view);
  }, [render, view]);

  useEffect(() => {
    const [stage, scene] = [stageRef.current, sceneRef.current];
    if (!stage || !scene || typeof ResizeObserver === "undefined") return undefined;
    // El ajuste se recalcula solo al cambiar el tamaño; girar no lo cambia.
    const observer = new ResizeObserver(() => {
      fit.current = fitToStage(stage, scene);
      render(current.current);
    });
    observer.observe(stage);
    return () => {
      observer.disconnect();
    };
  }, [render, stageRef, sceneRef]);

  return { view, setView, drag: useDrag(view, setView) };
}
