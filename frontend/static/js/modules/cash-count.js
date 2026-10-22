// Arqueo: vista previa del contado y de la diferencia mientras se cuentan los billetes. El servidor suma
// el contado de nuevo al cerrar (apps/cash/forms.py) y exige la nota si hay diferencia.
const form = document.querySelector("[data-cash-count]");

const peso = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
const cop = (value) => `${value < 0 ? "−" : ""}$${peso.format(Math.abs(value))}`;

function difference(value) {
  if (value === 0) return "Cuadrada";
  return value > 0 ? `▴ +${cop(value)} · sobrante` : `▾ ${cop(value)} · faltante`;
}

function preview() {
  const bills = [...form.querySelectorAll("[data-bill]")].reduce(
    (total, input) => total + Number(input.dataset.bill) * Number(input.value || 0),
    0,
  );
  const counted = bills + Number(form.querySelector("[data-coins]").value || 0);
  form.querySelector("[data-counted]").textContent = cop(counted);
  form.querySelector("[data-difference]").textContent = difference(counted - Number(form.dataset.expected));
}

if (form) {
  form.addEventListener("input", preview);
  preview();
}
