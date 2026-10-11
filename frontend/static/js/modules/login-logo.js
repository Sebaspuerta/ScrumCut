// Logo 3D del inicio de sesión (Login.dc.html): 12 capas que giran solo al arrastrarlas con el puntero.
// No hay giro automático, así que respeta prefers-reduced-motion sin más.

const LAYERS = 12;
const START = { x: 10, y: -22 };
const TILT_LIMIT = 45;

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

function stackLayers(body) {
  const front = body.firstElementChild;
  for (let depth = 1; depth < LAYERS; depth += 1) {
    const layer = front.cloneNode(true);
    layer.style.setProperty("--layer", depth);
    body.append(layer);
  }
}

function enableDrag(stage, body) {
  let rotation = { ...START };
  let drag = null;

  stage.addEventListener("pointerdown", (event) => {
    drag = { x: event.clientX, y: event.clientY, from: rotation };
    stage.setPointerCapture(event.pointerId);
  });

  stage.addEventListener("pointermove", (event) => {
    if (!drag) return;
    rotation = {
      x: clamp(drag.from.x - (event.clientY - drag.y) * 0.4, -TILT_LIMIT, TILT_LIMIT),
      y: drag.from.y + (event.clientX - drag.x) * 0.6,
    };
    body.style.transform = `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`;
  });

  const stop = () => {
    drag = null;
  };
  for (const name of ["pointerup", "pointercancel", "pointerleave"]) {
    stage.addEventListener(name, stop);
  }
}

for (const stage of document.querySelectorAll("[data-logo3d]")) {
  const body = stage.querySelector("[data-logo3d-body]");
  stackLayers(body);
  enableDrag(stage, body);
}
