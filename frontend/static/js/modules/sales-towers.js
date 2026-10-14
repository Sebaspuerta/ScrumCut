// Torres 3D de ventas por día (Main.dc.html). Los datos llegan listos del servidor con json_script:
// aquí solo se dibujan, se giran al arrastrar o con los botones y se lee el día bajo el cursor.
// Sin animaciones automáticas: solo se mueve cuando la persona lo pide (prefers-reduced-motion).

const STEP = 56; // distancia entre torres
const SIDE = 40; // lado de cada torre
const MAX_HEIGHT = 160; // altura de la torre del mejor día
const START = { tilt: 58, turn: -36 };
const TILT_RANGE = [20, 80];
const WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

const clamp = (value, [min, max]) => Math.max(min, Math.min(max, value));

function element(className, parent) {
  const node = document.createElement("div");
  node.className = className;
  parent.append(node);
  return node;
}

function place(node, column, row) {
  node.style.left = `${column * STEP}px`;
  node.style.top = `${row * STEP}px`;
}

function drawFloor(scene, cell, column, row) {
  const state = !cell.in_period ? "outside" : cell.closed ? "closed" : "open";
  place(element(`towers__floor towers__floor--${state}`, scene), column, row);
}

function drawTower(scene, cell, column, row) {
  const tower = element(`towers__tower towers__tower--level-${cell.level}`, scene);
  tower.classList.toggle("is-today", cell.today);
  place(tower, column, row);
  tower.style.setProperty("--height", `${Math.round(cell.ratio * MAX_HEIGHT)}px`);
  for (const face of ["north", "west", "south", "east", "top"]) element(`towers__face towers__face--${face}`, tower);
  return tower;
}

function drawAxis(scene, rows) {
  WEEKDAYS.forEach((name, column) => {
    const label = element("towers__axis", scene);
    label.textContent = name;
    label.style.left = `${column * STEP}px`;
    label.style.top = `${rows * STEP - (STEP - SIDE) + 10}px`;
  });
}

function buildScene(stage, weeks) {
  const scene = element("towers__scene", stage);
  scene.style.width = `${7 * STEP - (STEP - SIDE)}px`;
  scene.style.height = `${weeks.length * STEP - (STEP - SIDE)}px`;
  const towers = [];
  weeks.forEach((week, row) => {
    week.forEach((cell, column) => {
      drawFloor(scene, cell, column, row);
      if (cell.in_period && !cell.closed) towers.push({ cell, node: drawTower(scene, cell, column, row) });
    });
  });
  drawAxis(scene, weeks.length);
  return { scene, towers };
}

function enableReadout(towers, label, value) {
  let current = null;
  for (const { cell, node } of towers) {
    node.addEventListener("pointerenter", () => {
      current?.classList.remove("is-hovered");
      node.classList.add("is-hovered");
      current = node;
      label.textContent = cell.label;
      value.textContent = cell.amount;
    });
  }
}

const FIT_MARGIN = 24; // aire entre la escena y el borde del contenedor

const transformFor = (view, fit) =>
  `translate(${fit.x}px, ${fit.y}px) scale(${fit.scale}) rotateX(${view.tilt}deg) rotateZ(${view.turn}deg)`;

function projectedBox(stage) {
  // La caja de lo que se ve: pisos, techos de las torres y días, ya proyectados en la pantalla.
  const rects = [...stage.querySelectorAll(".towers__floor, .towers__face--top, .towers__axis")].map((node) =>
    node.getBoundingClientRect(),
  );
  const left = Math.min(...rects.map((rect) => rect.left));
  const top = Math.min(...rects.map((rect) => rect.top));
  const right = Math.max(...rects.map((rect) => rect.right));
  const bottom = Math.max(...rects.map((rect) => rect.bottom));
  return { width: right - left, height: bottom - top, centerX: (left + right) / 2, centerY: (top + bottom) / 2 };
}

function fitToStage(stage, scene) {
  // Escala y centrado de la vista inicial según el tamaño real del contenedor; se conservan al girar.
  const area = stage.getBoundingClientRect();
  scene.style.transform = transformFor(START, { x: 0, y: 0, scale: 1 });
  const natural = projectedBox(stage);
  const scale = Math.min(
    1,
    (area.width - 2 * FIT_MARGIN) / natural.width,
    (area.height - 2 * FIT_MARGIN) / natural.height,
  );
  scene.style.transform = transformFor(START, { x: 0, y: 0, scale });
  const scaled = projectedBox(stage);
  return {
    x: area.left + area.width / 2 - scaled.centerX,
    y: area.top + area.height / 2 - scaled.centerY,
    scale,
  };
}

function enableRotation(stage, scene, section) {
  let view = { ...START };
  let fit = { x: 0, y: 0, scale: 1 };
  let drag = null;
  const render = () => {
    scene.style.transform = transformFor(view, fit);
  };
  new ResizeObserver(() => {
    fit = fitToStage(stage, scene);
    render();
  }).observe(stage);
  stage.addEventListener("pointerdown", (event) => {
    drag = { x: event.clientX, y: event.clientY, from: view };
    stage.setPointerCapture(event.pointerId);
  });
  stage.addEventListener("pointermove", (event) => {
    if (!drag) return;
    view = {
      tilt: clamp(drag.from.tilt - (event.clientY - drag.y) * 0.3, TILT_RANGE),
      turn: drag.from.turn + (event.clientX - drag.x) * 0.4,
    };
    render();
  });
  for (const name of ["pointerup", "pointercancel", "pointerleave"]) stage.addEventListener(name, () => (drag = null));
  for (const button of section.querySelectorAll("[data-towers-turn]")) {
    button.addEventListener("click", () => {
      view = { ...view, turn: view.turn + Number(button.dataset.towersTurn) };
      render();
    });
  }
  section.querySelector("[data-towers-reset]").addEventListener("click", () => {
    view = { ...START };
    render();
  });
}

const stage = document.querySelector("[data-towers]");
if (stage) {
  const section = stage.closest("section");
  const weeks = JSON.parse(document.getElementById("towers-data").textContent);
  const { scene, towers } = buildScene(stage, weeks);
  enableReadout(towers, section.querySelector("[data-towers-label]"), section.querySelector("[data-towers-value]"));
  enableRotation(stage, scene, section);
}
