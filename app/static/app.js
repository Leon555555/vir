// app/static/app.js
console.log("app.js loaded");

// ============================
// Helper: POST JSON
// ============================
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

// ============================
// (Legacy) Toggle DONE / REDO
// ============================
document.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-action='toggle-done']");
  if (!btn) return;

  e.preventDefault();

  const itemId = btn.getAttribute("data-item-id");
  if (!itemId) return console.warn("Falta data-item-id");

  const forceRedo = btn.getAttribute("data-redo") === "1";
  btn.disabled = true;

  try {
    const out = await postJSON(`/rutina_item/${itemId}/toggle`, { redo: forceRedo });
    const done = !!out.done;

    const row = document.querySelector(`[data-rutina-item-row="${itemId}"]`);
    if (row) row.classList.toggle("is-done", done);

    btn.textContent = done ? "Redo" : "Hecho";
  } catch (err) {
    alert(err.message || "Error al marcar hecho");
  } finally {
    btn.disabled = false;
  }
});


// ======================================================
// PERFIL: modal full-screen + calendario + guardados
// ======================================================
let VR = {
  userId: null,
  apiDayDetail: null,
  apiCheckItem: null,
  apiSaveLog: null,
  apiBlockDay: null,
  staticPrefix: "",
  currentDate: null
};

function q(id) { return document.getElementById(id); }

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

function setText(id, text) {
  const el = q(id);
  if (el) el.textContent = text ?? "";
}

function escHtml(s) {
  return (s ?? "").toString()
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function activateTopTabs() {
  const tabs = document.querySelectorAll(".nav-vr-tabs .nav-link");
  const sections = {
    semana: document.getElementById("tab-semana"),
    calendario: document.getElementById("tab-calendario"),
    progreso: document.getElementById("tab-progreso"),
    rutinas: document.getElementById("tab-rutinas"),
  };

  function activateTab(name) {
    tabs.forEach(btn => btn.classList.toggle("active", btn.dataset.tab === name));
    Object.entries(sections).forEach(([key, sec]) => sec.classList.toggle("active", key === name));
  }

  tabs.forEach(btn => btn.addEventListener("click", () => activateTab(btn.dataset.tab)));
  activateTab("semana");
}

function bindWeekCardClicks() {
  document.querySelectorAll(".day-card[data-fecha]").forEach(card => {
    card.addEventListener("click", () => openDayDetail(card.dataset.fecha));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") openDayDetail(card.dataset.fecha);
    });
  });
}

function bindCalendarClicks() {
  document.querySelectorAll(".calendar-day[data-fecha]").forEach(cell => {
    cell.addEventListener("click", () => {
      const fecha = cell.dataset.fecha;
      const blocked = cell.dataset.blocked === "1";
      toggleBlockDay(fecha, blocked);
    });
    cell.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        const fecha = cell.dataset.fecha;
        const blocked = cell.dataset.blocked === "1";
        toggleBlockDay(fecha, blocked);
      }
    });
  });
}

function bindModalUI() {
  const modal = q("dayModal");
  const closeBtn = document.querySelector(".vr-modal-close");
  const saveBtn = q("btnSaveLog");

  // cerrar
  closeBtn?.addEventListener("click", closeDayModal);

  // cerrar con ESC / click afuera
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal && !modal.classList.contains("hidden")) closeDayModal();
  });
  modal?.addEventListener("click", (e) => {
    if (e.target === modal) closeDayModal();
  });

  // mini tabs propuesto (no fuerza)
  document.querySelectorAll(".vr-tab-mini").forEach(btn => {
    btn.addEventListener("click", () => switchPropuesto(btn.dataset.mini));
  });

  // guardar log
  saveBtn?.addEventListener("click", saveAthleteLog);
}

function switchPropuesto(which) {
  document.querySelectorAll(".vr-tab-mini").forEach(b => b.classList.toggle("active", b.dataset.mini === which));
  q("propuestoWarmup")?.classList.toggle("hidden", which !== "warmup");
  q("propuestoMain")?.classList.toggle("hidden", which !== "main");
  q("propuestoFinisher")?.classList.toggle("hidden", which !== "finisher");
}

function closeDayModal() {
  const modal = q("dayModal");
  if (!modal) return;
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

function openDayModal() {
  const modal = q("dayModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

async function openDayDetail(fechaISO) {
  VR.currentDate = fechaISO;
  setText("saveMsg", "");

  const url = `${VR.apiDayDetail}?user_id=${encodeURIComponent(VR.userId)}&fecha=${encodeURIComponent(fechaISO)}`;

  try {
    const res = await fetch(url, { credentials: "same-origin" });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Error");

    const plan = data.plan || {};
    const planType = (plan.plan_type || "descanso");
    const planTypeUpper = planType.toUpperCase();

    setText("modalTitle", planTypeUpper);
    setText("modalSubtitle", data.fecha || fechaISO);
    setText("modalTypeBadge", planTypeUpper);

    // log (lo realizado)
    const log = data.log || {};
    q("didTrainToggle").checked = !!log.did_train;
    q("warmupDone").value = log.warmup_done || "";
    q("mainDone").value = log.main_done || "";
    q("finisherDone").value = log.finisher_done || "";

    // fuerza vs no fuerza
    const isRutina = !!data.rutina;

    const propuestoBlocks = q("propuestoBlocks");
    const propuestoFuerza = q("propuestoFuerza");

    if (isRutina) {
      hide(propuestoBlocks);
      show(propuestoFuerza);

      setText("rutinaName", `Rutina: ${(data.rutina?.nombre || "")}`);

      const items = data.items || [];
      const doneIds = new Set(data.checks || []);
      const container = q("itemsList");
      container.innerHTML = "";

      items.forEach(it => {
        const done = doneIds.has(it.id);

        const metaParts = [];
        if (it.series) metaParts.push(`Series: ${escHtml(it.series)}`);
        if (it.reps) metaParts.push(`Reps: ${escHtml(it.reps)}`);
        if (it.descanso) metaParts.push(`Descanso: ${escHtml(it.descanso)}`);

        const meta = metaParts.length ? metaParts.join(" • ") : "";

        const videoHtml = it.video_url
          ? `<video controls preload="metadata">
               <source src="${VR.staticPrefix}${escHtml(it.video_url)}" type="video/mp4">
             </video>`
          : "";

        const noteHtml = it.nota ? `<div class="vr-item-note">${escHtml(it.nota)}</div>` : "";

        const el = document.createElement("div");
        el.className = "vr-item";
        el.innerHTML = `
          <div class="vr-item-head">
            <div class="vr-item-name">${escHtml(it.nombre)}</div>
            <button class="btn btn-sm ${done ? "btn-success" : "btn-outline-info"}"
                    type="button"
                    data-action="item-done"
                    data-item-id="${it.id}"
                    data-next="${done ? "0" : "1"}">
              ${done ? "✅ Realizado" : "Marcar"}
            </button>
          </div>
          ${meta ? `<div class="vr-item-meta">${meta}</div>` : ""}
          ${videoHtml}
          ${noteHtml}
        `;
        container.appendChild(el);
      });

    } else {
      hide(propuestoFuerza);
      show(propuestoBlocks);

      // No fuerza: propuesto (3 paneles)
      setText("propuestoWarmup", plan.warmup || "—");
      setText("propuestoMain", plan.main || "—");
      setText("propuestoFinisher", plan.finisher || "—");
      switchPropuesto("warmup");
    }

    openDayModal();

  } catch (err) {
    alert(err.message || "No se pudo cargar el detalle");
  }
}

// Click dentro del modal para marcar ejercicios de fuerza
document.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-action='item-done']");
  if (!btn) return;

  e.preventDefault();
  e.stopPropagation();

  const itemId = parseInt(btn.dataset.itemId, 10);
  const next = btn.dataset.next === "1";

  btn.disabled = true;
  try {
    const form = new FormData();
    form.append("user_id", VR.userId);
    form.append("fecha", VR.currentDate);
    form.append("item_id", itemId);
    form.append("done", next ? "1" : "0");

    const res = await fetch(VR.apiCheckItem, { method: "POST", body: form, credentials: "same-origin" });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Error");

    // UI
    btn.classList.toggle("btn-success", next);
    btn.classList.toggle("btn-outline-info", !next);
    btn.textContent = next ? "✅ Realizado" : "Marcar";
    btn.dataset.next = next ? "0" : "1";

  } catch (err) {
    alert(err.message || "No se pudo guardar");
  } finally {
    btn.disabled = false;
  }
});

async function saveAthleteLog() {
  const saveMsg = q("saveMsg");
  saveMsg.textContent = "Guardando...";

  const payload = {
    user_id: VR.userId,
    fecha: VR.currentDate,
    did_train: !!q("didTrainToggle").checked,
    warmup_done: q("warmupDone").value || "",
    main_done: q("mainDone").value || "",
    finisher_done: q("finisherDone").value || "",
  };

  try {
    const out = await postJSON(VR.apiSaveLog, payload);
    if (!out.ok) throw new Error(out.error || "Error");
    saveMsg.textContent = "Guardado ✔";
  } catch (err) {
    saveMsg.textContent = "";
    alert(err.message || "No se pudo guardar");
  }
}

async function toggleBlockDay(fechaISO, currentlyBlocked) {
  const next = !currentlyBlocked;

  try {
    const out = await postJSON(VR.apiBlockDay, {
      user_id: VR.userId,
      fecha: fechaISO,
      blocked: next
    });

    if (!out.ok) throw new Error(out.error || "Error");

    // Reflejo rápido: recargar (simple y seguro)
    window.location.reload();

  } catch (err) {
    alert(err.message || "No se pudo bloquear/desbloquear");
  }
}

// Boot
document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("perfilRoot");
  if (!root) return;

  VR.userId = parseInt(root.dataset.userId, 10);
  VR.apiDayDetail = root.dataset.apiDayDetail;
  VR.apiCheckItem = root.dataset.apiCheckItem;
  VR.apiSaveLog = root.dataset.apiSaveLog;
  VR.apiBlockDay = root.dataset.apiBlockDay;
  VR.staticPrefix = root.dataset.staticPrefix || "";

  activateTopTabs();
  bindWeekCardClicks();
  bindCalendarClicks();
  bindModalUI();
});
