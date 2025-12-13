// app/static/dragdrop.js
console.log("dragdrop.js loaded");

// Requisitos mínimos en tu HTML:
// - El "bloque" rutina debe tener draggable="true" y data-rutina-id="123"
// - Cada "columna día" debe tener data-drop-date="YYYY-MM-DD"

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

  const text = await res.text();
  let payload = null;
  try { payload = JSON.parse(text); } catch { payload = { raw: text }; }

  if (!res.ok) {
    const msg = payload?.error || payload?.raw || `Error HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

let draggedRutinaId = null;

document.addEventListener("dragstart", (e) => {
  const card = e.target.closest("[data-rutina-id]");
  if (!card) return;
  draggedRutinaId = card.getAttribute("data-rutina-id");
  e.dataTransfer?.setData("text/plain", draggedRutinaId);
  e.dataTransfer?.setDragImage?.(card, 10, 10);
  card.classList.add("is-dragging");
});

document.addEventListener("dragend", (e) => {
  const card = e.target.closest("[data-rutina-id]");
  if (card) card.classList.remove("is-dragging");
  draggedRutinaId = null;
});

document.addEventListener("dragover", (e) => {
  const zone = e.target.closest("[data-drop-date]");
  if (!zone) return;
  e.preventDefault();
  zone.classList.add("is-over");
});

document.addEventListener("dragleave", (e) => {
  const zone = e.target.closest("[data-drop-date]");
  if (!zone) return;
  zone.classList.remove("is-over");
});

document.addEventListener("drop", async (e) => {
  const zone = e.target.closest("[data-drop-date]");
  if (!zone) return;
  e.preventDefault();
  zone.classList.remove("is-over");

  const rutId = draggedRutinaId || e.dataTransfer?.getData("text/plain");
  const newDate = zone.getAttribute("data-drop-date");
  if (!rutId || !newDate) return;

  try {
    await postJSON("/rutina/mover", { rutina_id: rutId, nueva_fecha: newDate });
    // opción rápida: recargar para ver cambios sin complicarte el DOM
    window.location.reload();
  } catch (err) {
    alert(err.message || "Error al mover rutina");
  }
});
