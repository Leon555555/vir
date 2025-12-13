// app/static/app.js
console.log("app.js loaded");

// Helper: POST JSON (con soporte CSRF si lo agregás por meta)
async function postJSON(url, data) {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");
  const headers = { "Content-Type": "application/json" };
  if (csrf) headers["X-CSRFToken"] = csrf;

  const res = await fetch(url, {
    method: "POST",
    headers,
    credentials: "same-origin",
    body: JSON.stringify(data || {}),
  });

  // Si el servidor devuelve HTML por error, igualmente lo mostramos
  const text = await res.text();
  let payload = null;
  try { payload = JSON.parse(text); } catch { payload = { raw: text }; }

  if (!res.ok) {
    const msg = payload?.error || payload?.raw || `Error HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

// Toggle DONE / REDO
document.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-action='toggle-done']");
  if (!btn) return;

  e.preventDefault();

  const itemId = btn.getAttribute("data-item-id");
  if (!itemId) return console.warn("Falta data-item-id");

  // Opcional: si tu botón tiene data-redo="1" forzás redo
  const forceRedo = btn.getAttribute("data-redo") === "1";

  btn.disabled = true;
  try {
    const out = await postJSON(`/rutina_item/${itemId}/toggle`, { redo: forceRedo });

    // Espera que el server devuelva: { ok: true, done: bool }
    const done = !!out.done;

    // UI: clase en el row padre si existe
    const row = document.querySelector(`[data-rutina-item-row="${itemId}"]`);
    if (row) row.classList.toggle("is-done", done);

    // UI: texto del botón
    btn.textContent = done ? "Redo" : "Hecho";

  } catch (err) {
    alert(err.message || "Error al marcar hecho");
  } finally {
    btn.disabled = false;
  }
});
