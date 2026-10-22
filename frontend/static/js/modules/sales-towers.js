// Torres 3D de ventas por día (Main.dc.html), con transformaciones CSS. Los datos llegan listos del
// servidor (json_script): aquí solo se dibujan, se giran al arrastrar o con los botones y se muestra
// el día bajo el cursor. Sin animaciones automáticas: solo se mueve cuando la persona lo pide.

const STEP = 56; // distancia entre torres
const SIDE = 40; // lado de cada torre
const MAX_HEIGHT = 160; // altura de la torre del mejor día
const START = { tilt: 58, turn: -36 };
const TILT_RANGE = [20, 80];
const FIT_MARGIN = 24; // aire entre la escena y el borde del contenedor
const TOOLTIP_OFFSET = 14; // el recuadro queda junto al cursor, sin taparlo
const WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

const clamp = (value, [min, max]) => Math.max(min, Math.min(max, value));

function element(className, parent, text = "") {
  const node = document.createElement("div");
  node.className = className;
  node.textContent = text;
  parent.append(node);
  return node;
}

function place(node, column, row) {
  node.style.left = `${column * STEP}px`;
  node.style.top = `${row * STEP}px`;
}

function floorState(cell) {
  if (!cell) return "outside";
  return cell.future ? "future" : "open";
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
    const label = element("towers__axis", scene, name);
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
      const floor = element(`towers__floor towers__floor--${floorState(cell)}`, scene, cell ? String(cell.day) : "");
      place(floor, column, row);
      if (cell?.has_sales && !cell.future) towers.push({ cell, node: drawTower(scene, cell, column, row) });
    });
  });
  drawAxis(scene, weeks.length);
  return { scene, towers };
}

function enableTooltip(stage, towers) {
  const tooltip = stage.querySelector("[data-towers-tooltip]");
  const [label, value] = [tooltip.querySelector("[data-towers-label]"), tooltip.querySelector("[data-towers-value]")];
  for (const { cell, node } of towers) {
    node.addEventListener("pointerenter", () => {
      node.classList.add("is-hovered");
      label.textContent = cell.label;
      value.textContent = cell.amount;
      tooltip.hidden = false;
    });
    node.addEventListener("pointerleave", () => {
      node.classList.remove("is-hovered");
      tooltip.hidden = true;
    });
  }
  stage.addEventListener("pointermove", (event) => {
    const area = stage.getBoundingClientRect();
    tooltip.style.left = `${event.clientX - area.left + TOOLTIP_OFFSET}px`;
    tooltip.style.top = `${event.clientY - area.top + TOOLTIP_OFFSET}px`;
  });
}

const transformFor = (view, fit) =>
  `translate(${fit.x}px, ${fit.y}px) scale(${fit.scale}) rotateX(${view.tilt}deg) rotateZ(${view.turn}deg)`;

function projectedBox(stage) {
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
  const scale = Math.min(1, (area.width - 2 * FIT_MARGIN) / natural.width, (area.height - 2 * FIT_MARGIN) / natural.height);
  scene.style.transform = transformFor(START, { x: 0, y: 0, scale });
  const scaled = projectedBox(stage);
  return { x: area.left + area.width / 2 - scaled.centerX, y: area.top + area.height / 2 - scaled.centerY, scale };
}

function enableDrag(stage, state, render) {
  let drag = null;
  stage.addEventListener("pointerdown", (event) => {
    drag = { x: event.clientX, y: event.clientY, from: state.view };
    stage.setPointerCapture(event.pointerId);
  });
  stage.addEventListener("pointermove", (event) => {
    if (!drag) return;
    state.view = {
      tilt: clamp(drag.from.tilt - (event.clientY - drag.y) * 0.3, TILT_RANGE),
      turn: drag.from.turn + (event.clientX - drag.x) * 0.4,
    };
    render();
  });
  for (const name of ["pointerup", "pointercancel"]) stage.addEventListener(name, () => (drag = null));
}

function enableRotation(container, stage, scene) {
  const state = { view: { ...START }, fit: { x: 0, y: 0, scale: 1 } };
  const render = () => (scene.style.transform = transformFor(state.view, state.fit));
  new ResizeObserver(() => {
    state.fit = fitToStage(stage, scene);
    render();
  }).observe(stage);
  enableDrag(stage, state, render);
  for (const button of container.querySelectorAll("[data-towers-turn]")) {
    button.addEventListener("click", () => {
      state.view = { ...state.view, turn: state.view.turn + Number(button.dataset.towersTurn) };
      render();
    });
  }
  container.querySelector("[data-towers-reset]").addEventListener("click", () => {
    state.view = { ...START };
    render();
  });
}

// Solo se carga en ?vista=3d: el servidor decide la vista y aquí no se guarda nada en el navegador.
const container = document.querySelector("[data-sales-3d]");
if (container) {
  const stage = container.querySelector("[data-towers]");
  const weeks = JSON.parse(document.getElementById("sales-chart-data").textContent);
  const { scene, towers } = buildScene(stage, weeks);
  enableTooltip(stage, towers);
  enableRotation(container, stage, scene);
}
