// app/static/js/perfil.js

document.addEventListener("DOMContentLoaded", () => {
  // ==========================
  // Helpers
  // ==========================
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  function getUserId() {
    // 1) window.__USER_ID__ (recomendado)
    if (window.__USER_ID__) return parseInt(window.__USER_ID__, 10);

    // 2) dataset en body
    const b = document.body;
    if (b && b.dataset && b.dataset.userId) return parseInt(b.dataset.userId, 10);

    // 3) hidden input
    const inp = document.getElementById("currentUserId");
    if (inp && inp.value) return parseInt(inp.value, 10);

    // 4) fallback: /perfil/<id>
    const m = (location.pathname || "").match(/\/perfil\/(\d+)/);
    if (m) return parseInt(m[1], 10);

    return null;
  }

  function fmtDateLabel(iso) {
    // iso: YYYY-MM-DD
    try {
      const [y, mo, d] = iso.split("-").map((x) => parseInt(x, 10));
      return `${String(d).padStart(2, "0")}/${String(mo).padStart(2, "0")}/${y}`;
    } catch {
      return iso;
    }
  }

  function escapeHtml(s) {
    return String(s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  // ==========================
  // Modal refs (necesarios)
  // ==========================
  const modalEl = document.getElementById("dayDetailModal");
  const modalTitleEl = document.getElementById("dayDetailTitle");
  const modalBodyEl = document.getElementById("dayDetailBody");

  if (!modalEl || !modalTitleEl || !modalBodyEl) {
    console.warn("[perfil.js] Falta el modal #dayDetailModal/#dayDetailTitle/#dayDetailBody en perfil.html");
    return;
  }

  let bsModal = null;
  try {
    bsModal = new bootstrap.Modal(modalEl);
  } catch (e) {
    console.warn("[perfil.js] Bootstrap modal no disponible", e);
  }

  // ==========================
  // Render modal content
  // ==========================
  function renderDayDetail(data, userId, fechaISO) {
    const plan = data.plan || {};
    const rutina = data.rutina || null;
    const items = Array.isArray(data.items) ? data.items : [];
    const checks = new Set(Array.isArray(data.checks) ? data.checks : []);
    const log = data.log || {};
    const tabataUrl = data.tabata_url || "";

    // Header
    const rutinaTitle = rutina ? `${escapeHtml(rutina.nombre)}${rutina.tipo ? ` <span class="badge bg-secondary ms-2">${escapeHtml(rutina.tipo)}</span>` : ""}` : "—";
    const planType = (plan.plan_type || "Descanso");

    modalTitleEl.innerHTML = `
      <div class="d-flex align-items-center justify-content-between gap-2 flex-wrap">
        <div>
          <div style="font-weight:900; letter-spacing:.08em; text-transform:uppercase; opacity:.75; font-size:.85rem;">
            ${fmtDateLabel(fechaISO)}
          </div>
          <div style="font-size:1.25rem; font-weight:900;">
            ${rutina ? rutinaTitle : escapeHtml(planType)}
          </div>
        </div>
        <div class="badge bg-info">${escapeHtml(planType)}</div>
      </div>
    `;

    // Botón TABATA (si existe)
    const tabataBtn = tabataUrl
      ? `
        <div class="d-grid mb-3">
          <a class="btn btn-info" href="${tabataUrl}">
            ▶ Iniciar TABATA
          </a>
        </div>
      `
      : "";

    // Plan blocks
    const warmup = escapeHtml(plan.warmup || "—");
    const main = escapeHtml(plan.main || "—");
    const finisher = escapeHtml(plan.finisher || "—");

    // Disponibilidad
    const puede = (plan.puede_entrenar || "si") === "si";
    const comentarioAtleta = escapeHtml(plan.comentario_atleta || "");

    // Log atleta
    const didTrain = !!log.did_train;

    // Items list
    let itemsHtml = "";
    if (items.length) {
      itemsHtml = items.map((it, idx) => {
        const done = checks.has(it.id);
        const videoSrc = it.video_src || "";
        const hasVideo = !!videoSrc;

        return `
          <div class="card glass mb-3">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start gap-2">
                <div>
                  <div class="text-strong" style="font-size:1.05rem;">${escapeHtml(it.nombre)}</div>
                  <div class="text-soft" style="font-size:.9rem;">
                    ${it.series ? `<span class="me-2">Series: <b>${escapeHtml(it.series)}</b></span>` : ""}
                    ${it.reps ? `<span class="me-2">Reps: <b>${escapeHtml(it.reps)}</b></span>` : ""}
                    ${it.peso ? `<span class="me-2">Peso: <b>${escapeHtml(it.peso)}</b></span>` : ""}
                    ${it.descanso ? `<span class="me-2">Desc: <b>${escapeHtml(it.descanso)}</b></span>` : ""}
                  </div>
                </div>

                <div class="d-flex align-items-center gap-2">
                  <div class="form-check form-switch m-0">
                    <input class="form-check-input js-item-check"
                           type="checkbox"
                           data-item-id="${it.id}"
                           ${done ? "checked" : ""}>
                  </div>
                  <span class="text-soft" style="font-size:.85rem;">HECHO</span>
                </div>
              </div>

              ${hasVideo ? `
                <div class="mt-3" style="border-radius:18px; overflow:hidden; border:1px solid rgba(255,255,255,.12); background:#000;">
                  <video class="w-100" controls playsinline preload="metadata" src="${videoSrc}"></video>
                </div>
              ` : `
                <div class="mt-3 text-soft">Sin video</div>
              `}

              ${it.nota ? `<div class="mt-2 text-soft"><b>Nota:</b> ${escapeHtml(it.nota)}</div>` : ""}
            </div>
          </div>
        `;
      }).join("");
    } else {
      itemsHtml = `<div class="text-soft">No hay items en la rutina.</div>`;
    }

    // Montaje final del modal
    modalBodyEl.innerHTML = `
      <input type="hidden" id="dd_user_id" value="${userId}">
      <input type="hidden" id="dd_fecha" value="${fechaISO}">

      <div class="row g-3">
        <!-- Plan -->
        <div class="col-12 col-lg-4">
          <div class="card glass lift">
            <div class="card-header">
              <strong>Plan</strong>
            </div>
            <div class="card-body">

              ${tabataBtn}

              <div class="mb-2">
                <div class="text-muted" style="font-weight:900; letter-spacing:.08em; text-transform:uppercase; font-size:.8rem;">Activación</div>
                <div class="p-3 mt-1" style="border:1px solid rgba(255,255,255,.10); border-radius:14px; background:rgba(255,255,255,.03);">
                  ${warmup}
                </div>
              </div>

              <div class="mb-2">
                <div class="text-muted" style="font-weight:900; letter-spacing:.08em; text-transform:uppercase; font-size:.8rem;">Bloque principal</div>
                <div class="p-3 mt-1" style="border:1px solid rgba(255,255,255,.10); border-radius:14px; background:rgba(255,255,255,.03);">
                  ${rutina ? `<b>RUTINA:</b> ${escapeHtml(String(rutina.id))}` : main}
                </div>
              </div>

              <div class="mb-3">
                <div class="text-muted" style="font-weight:900; letter-spacing:.08em; text-transform:uppercase; font-size:.8rem;">Enfriamiento</div>
                <div class="p-3 mt-1" style="border:1px solid rgba(255,255,255,.10); border-radius:14px; background:rgba(255,255,255,.03);">
                  ${finisher}
                </div>
              </div>

              <div class="mb-2">
                <div class="d-flex justify-content-between align-items-center">
                  <div class="text-muted" style="font-weight:900; letter-spacing:.08em; text-transform:uppercase; font-size:.8rem;">Disponibilidad</div>
                  <span class="badge ${puede ? "bg-success" : "bg-danger"}">${puede ? "OK" : "NO"}</span>
                </div>

                <div class="form-check form-switch mt-2">
                  <input class="form-check-input" type="checkbox" id="dd_no_puedo" ${puede ? "" : "checked"}>
                  <label class="form-check-label text-soft" for="dd_no_puedo">No puedo entrenar este día</label>
                </div>

                <textarea id="dd_comentario" class="form-control mt-2" rows="3"
                  placeholder="Ej: viaje / lesión / trabajo / etc (corto)">${comentarioAtleta}</textarea>

                <div class="d-grid mt-2">
                  <button class="btn btn-outline-danger" id="dd_save_availability">Guardar bloqueo</button>
                </div>

                <div class="text-soft mt-2" style="font-size:.85rem;">
                  Si bloqueás el día, el coach lo verá en rojo y no planifica.
                </div>
              </div>

            </div>
          </div>
        </div>

        <!-- Realizado + Items -->
        <div class="col-12 col-lg-8">
          <div class="card glass lift mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
              <strong>Lo realizado</strong>

              <div class="d-flex align-items-center gap-2">
                <span class="text-soft">Hoy entrené</span>
                <div class="form-check form-switch m-0">
                  <input class="form-check-input" type="checkbox" id="dd_did_train" ${didTrain ? "checked" : ""}>
                </div>
              </div>
            </div>
            <div class="card-body">

              <div class="row g-2 mb-3">
                <div class="col-12 col-md-4">
                  <label class="text-soft" style="font-size:.85rem;">Warmup hecho</label>
                  <input id="dd_warmup_done" class="form-control" value="${escapeHtml(log.warmup_done || "")}">
                </div>
                <div class="col-12 col-md-4">
                  <label class="text-soft" style="font-size:.85rem;">Main hecho</label>
                  <input id="dd_main_done" class="form-control" value="${escapeHtml(log.main_done || "")}">
                </div>
                <div class="col-12 col-md-4">
                  <label class="text-soft" style="font-size:.85rem;">Finisher hecho</label>
                  <input id="dd_finisher_done" class="form-control" value="${escapeHtml(log.finisher_done || "")}">
                </div>
                <div class="col-12">
                  <div class="d-grid">
                    <button class="btn btn-outline-info" id="dd_save_log">Guardar realizado</button>
                  </div>
                </div>
              </div>

              ${itemsHtml}

            </div>
          </div>
        </div>
      </div>
    `;

    // bind actions
    bindDayDetailActions();
  }

  // ==========================
  // Actions inside modal
  // ==========================
  function bindDayDetailActions() {
    // Checks por item
    $$(".js-item-check").forEach((chk) => {
      chk.addEventListener("change", async () => {
        const userId = parseInt($("#dd_user_id").value, 10);
        const fecha = $("#dd_fecha").value;
        const itemId = parseInt(chk.dataset.itemId, 10);
        const done = chk.checked;

        const fd = new FormData();
        fd.append("user_id", String(userId));
        fd.append("fecha", fecha);
        fd.append("item_id", String(itemId));
        fd.append("done", done ? "1" : "0");

        try {
          const res = await fetch("/athlete/check_item", { method: "POST", body: fd });
          const data = await res.json();
          if (!data.ok) {
            alert("Error guardando check: " + (data.error || "—"));
            chk.checked = !done;
          }
        } catch (e) {
          alert("Error de red guardando check.");
          chk.checked = !done;
        }
      });
    });

    // Guardar disponibilidad
    const btnAvail = $("#dd_save_availability");
    if (btnAvail) {
      btnAvail.addEventListener("click", async () => {
        const userId = parseInt($("#dd_user_id").value, 10);
        const fecha = $("#dd_fecha").value;
        const noPuedo = !!$("#dd_no_puedo").checked;
        const comentario = ($("#dd_comentario").value || "").trim();

        try {
          const res = await fetch("/athlete/save_availability", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_id: userId,
              fecha: fecha,
              no_puedo: noPuedo,
              comentario: comentario
            })
          });
          const data = await res.json();
          if (!data.ok) {
            alert("Error guardando disponibilidad: " + (data.error || "—"));
            return;
          }
          // recargar para que se pinte en UI si tu template usa planes del server
          location.reload();
        } catch (e) {
          alert("Error de red guardando disponibilidad.");
        }
      });
    }

    // Guardar log
    const btnLog = $("#dd_save_log");
    if (btnLog) {
      btnLog.addEventListener("click", async () => {
        const userId = parseInt($("#dd_user_id").value, 10);
        const fecha = $("#dd_fecha").value;
        const didTrain = !!$("#dd_did_train").checked;
        const warmupDone = ($("#dd_warmup_done").value || "").trim();
        const mainDone = ($("#dd_main_done").value || "").trim();
        const finisherDone = ($("#dd_finisher_done").value || "").trim();

        try {
          const res = await fetch("/athlete/save_log", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_id: userId,
              fecha: fecha,
              did_train: didTrain,
              warmup_done: warmupDone,
              main_done: mainDone,
              finisher_done: finisherDone
            })
          });
          const data = await res.json();
          if (!data.ok) {
            alert("Error guardando realizado: " + (data.error || "—"));
            return;
          }
          // opcional: feedback
          btnLog.textContent = "✅ Guardado";
          setTimeout(() => (btnLog.textContent = "Guardar realizado"), 1200);
        } catch (e) {
          alert("Error de red guardando realizado.");
        }
      });
    }
  }

  // ==========================
  // Abrir modal desde calendario
  // ==========================
  const userId = getUserId();
  if (!userId) {
    console.warn("[perfil.js] No pude detectar user_id.");
  }

  // IMPORTANTE:
  // Tus celdas deben tener: class="day-cell" y data-fecha="YYYY-MM-DD"
  $$(".day-cell").forEach((cell) => {
    cell.addEventListener("click", async () => {
      const fechaISO = cell.dataset.fecha || cell.dataset.dia; // fallback
      if (!fechaISO) return;

      try {
        const url = `/api/day_detail?user_id=${encodeURIComponent(userId)}&fecha=${encodeURIComponent(fechaISO)}`;
        const res = await fetch(url);
        const data = await res.json();

        if (!data.ok) {
          alert("Error cargando día: " + (data.error || "—"));
          return;
        }

        renderDayDetail(data, userId, fechaISO);

        if (bsModal) bsModal.show();
      } catch (e) {
        alert("Error de red cargando el día.");
      }
    });
  });

});
