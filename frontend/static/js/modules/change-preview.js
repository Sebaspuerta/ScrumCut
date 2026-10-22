// Cobro de una comanda: muestra solo los campos de la forma de pago elegida y una vista previa de las
// vueltas. El servidor vuelve a calcularlas al cobrar (apps/sales/services/checkout.py); esto es solo ayuda.
const form = document.querySelector("[data-checkout]");

const peso = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
const cop = (value) => `${value < 0 ? "−" : ""}$${peso.format(Math.abs(value))}`;

function showMethod(method) {
  for (const group of form.querySelectorAll("[data-method]")) group.hidden = group.dataset.method !== method;
}

function previewChange() {
  const received = Number(form.querySelector("[data-received]").value || 0);
  const change = received - Number(form.dataset.total);
  form.querySelector("[data-change]").textContent = change >= 0 ? cop(change) : `Faltan ${cop(-change)}`;
}

if (form) {
  for (const radio of form.querySelectorAll("input[name='metodo']")) {
    radio.addEventListener("change", () => showMethod(radio.value));
  }
  form.querySelector("[data-received]").addEventListener("input", previewChange);
  showMethod(form.querySelector("input[name='metodo']:checked").value);
}
