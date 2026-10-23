// Abono a un fiado: vista previa del saldo después del abono. El servidor valida que el monto sea mayor
// que cero y no pase el saldo (apps/receivables/services.py); esto es solo ayuda.
const form = document.querySelector("[data-payment]");

const peso = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
const cop = (value) => `$${peso.format(value)}`;

function preview() {
  const balance = Number(form.dataset.balance);
  const typed = form.querySelector("[data-amount]").value;
  const after = balance - Number(typed || 0);
  const note = form.querySelector("[data-after]");
  if (typed === "") note.textContent = "";
  else if (after < 0) note.textContent = `El abono pasa el saldo por ${cop(-after)}.`;
  else note.textContent = after === 0 ? "Con este abono el fiado queda pagado." : `Saldo después del abono: ${cop(after)}.`;
}

if (form) {
  form.addEventListener("input", preview);
  preview();
}
