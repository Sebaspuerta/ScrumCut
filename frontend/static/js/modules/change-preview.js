// Cobro de una comanda: muestra los campos de la forma de pago elegida, abre las filas para dividir el
// pago y muestra una vista previa de la suma y de las vueltas sobre la parte en efectivo. El servidor
// vuelve a validar todo al cobrar (apps/sales/services/checkout.py); esto es solo ayuda.
const form = document.querySelector("[data-checkout]");

const CASH = "efectivo";
const peso = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
const cop = (value) => `${value < 0 ? "−" : ""}$${peso.format(Math.abs(value))}`;
const total = () => Number(form.dataset.total);
const splitOpen = () => !form.querySelector("[data-split]").hidden;

function parts() {
  return [...form.querySelectorAll(".checkout__part")]
    .map((row) => ({
      method: row.querySelector("[data-part-method]").value,
      amount: Number(row.querySelector("[data-part-amount]").value || 0),
    }))
    .filter((part) => part.method && part.amount);
}

function chosenMethods() {
  if (splitOpen()) return parts().map((part) => part.method);
  return [form.querySelector("input[name='metodo']:checked").value];
}

function showGroups() {
  const methods = chosenMethods();
  for (const group of form.querySelectorAll("[data-method]")) {
    const owners = group.dataset.method.split(/\s+/);
    const isReference = !owners.includes(CASH) && !owners.includes("fiado");
    group.hidden = !methods.some((method) => owners.includes(method)) || (isReference && splitOpen());
  }
}

function cashToCharge() {
  if (!splitOpen()) return chosenMethods()[0] === CASH ? total() : 0;
  return parts().reduce((sum, part) => sum + (part.method === CASH ? part.amount : 0), 0);
}

function preview() {
  showGroups();
  const typed = form.querySelector("[data-received]").value;
  const change = Number(typed || 0) - cashToCharge();
  const text = change >= 0 ? cop(change) : `Faltan ${cop(-change)}`;
  form.querySelector("[data-change]").textContent = typed === "" ? "—" : text;
  if (splitOpen()) {
    const sum = parts().reduce((acc, part) => acc + part.amount, 0);
    const note = sum === total() ? "Las partes suman el total." : `Suman ${cop(sum)} de ${cop(total())}.`;
    form.querySelector("[data-split-sum]").textContent = note;
  }
}

function openSplit(button) {
  form.querySelector("[data-split]").hidden = false;
  form.querySelector("[data-single]").hidden = true;
  button.hidden = true;
  form.querySelector("[data-part-method]").focus();
  preview();
}

if (form) {
  const splitButton = form.querySelector("[data-split-open]");
  splitButton.hidden = false;
  splitButton.addEventListener("click", () => openSplit(splitButton));
  form.addEventListener("input", preview);
  form.addEventListener("change", preview);
  preview();
}
