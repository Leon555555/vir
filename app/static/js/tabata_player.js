(function () {
  const items = Array.isArray(window.__TABATA_ITEMS__) ? window.__TABATA_ITEMS__ : [];

  const $ = (id) => document.getElementById(id);

  const cfgWork = $("cfgWork");
  const cfgRest = $("cfgRest");
  const cfgRounds = $("cfgRounds");
  const cfgRecovery = $("cfgRecovery");

  const btnApply = $("btnApply");
  const btnStart = $("btnStart");
  const btnPause = $("btnPause");
  const btnReset = $("btnReset");

  const timerBig = $("timerBig");
  const timerHint = $("timerHint");
  const stateLabel = $("stateLabel");
  const roundLabel = $("roundLabel");
  const roundTotal = $("roundTotal");

  const exTitle = $("exTitle");
  const exNote = $("exNote");
  const exVideo = $("exVideo");
  const queue = $("queue");
  const phaseBadge = $("phaseBadge");

  function pad2(n) { return String(n).padStart(2, "0"); }
  function mmss(s) {
    s = Math.max(0, Math.floor(s));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${pad2(m)}:${pad2(r)}`;
  }

  let config = {
    work: parseInt(cfgWork.value || "40", 10),
    rest: parseInt(cfgRest.value || "20", 10),
    rounds: parseInt(cfgRounds.value || String(items.length || 10), 10),
    recovery: parseInt(cfgRecovery.value || "60", 10),
  };

  function sanitizeConfig() {
    config.work = Math.max(5, parseInt(cfgWork.value || "40", 10));
    config.rest = Math.max(0, parseInt(cfgRest.value || "20", 10));
    config.rounds = Math.max(1, parseInt(cfgRounds.value || String(items.length || 10), 10));
    config.recovery = Math.max(0, parseInt(cfgRecovery.value || "60", 10));
    cfgWork.value = config.work;
    cfgRest.value = config.rest;
    cfgRounds.value = config.rounds;
    cfgRecovery.value = config.recovery;
  }

  function getSeq() {
    if (!items.length) return [];
    const seq = [];
    for (let i = 0; i < config.rounds; i++) {
      seq.push(items[i % items.length]);
    }
    return seq;
  }

  let seq = getSeq();
  roundTotal.textContent = String(seq.length);

  let phase = "idle"; // work | rest | recovery | done | idle
  let idx = 0;
  let remaining = 0;
  let running = false;
  let interval = null;

  function setUIState() {
    btnStart.disabled = running;
    btnPause.disabled = !running;
    btnReset.disabled = (phase === "idle");
  }

  function escapeHtml(s) {
    return String(s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function renderQueue() {
    const next = [];
    for (let i = idx; i < Math.min(idx + 5, seq.length); i++) {
      next.push(`<span class="badge bg-secondary me-2 mb-2">${i + 1}. ${escapeHtml(seq[i].nombre || "—")}</span>`);
    }
    queue.innerHTML = next.length ? next.join("") : `<div class="text-soft">—</div>`;
  }

  function loadExercise(i) {
    const it = seq[i];
    if (!it) {
      exTitle.textContent = "—";
      exNote.textContent = "";
      exVideo.removeAttribute("src");
      exVideo.load();
      return;
    }
    exTitle.textContent = it.nombre || "—";
    exNote.textContent = it.nota || "";
    if (it.video_src) {
      try { exVideo.pause(); } catch(e) {}
      exVideo.src = it.video_src;
      exVideo.load();
    } else {
      exVideo.removeAttribute("src");
      exVideo.load();
    }
  }

  function setPhase(p, seconds) {
    phase = p;
    remaining = seconds;
    timerBig.textContent = mmss(remaining);

    if (phase === "work") {
      phaseBadge.textContent = "WORK";
      phaseBadge.className = "badge bg-success";
      timerHint.textContent = "Trabajo";
      stateLabel.textContent = "Trabajando";
    } else if (phase === "rest") {
      phaseBadge.textContent = "REST";
      phaseBadge.className = "badge bg-warning text-dark";
      timerHint.textContent = "Descanso";
      stateLabel.textContent = "Descansando";
    } else if (phase === "recovery") {
      phaseBadge.textContent = "RECOVERY";
      phaseBadge.className = "badge bg-info";
      timerHint.textContent = "Recuperación final";
      stateLabel.textContent = "Recuperación";
    } else if (phase === "done") {
      phaseBadge.textContent = "DONE";
      phaseBadge.className = "badge bg-secondary";
      timerHint.textContent = "Finalizado";
      stateLabel.textContent = "Terminado ✅";
      timerBig.textContent = "00:00";
    } else {
      phaseBadge.textContent = "—";
      phaseBadge.className = "badge bg-secondary";
      timerHint.textContent = "Preparado";
      stateLabel.textContent = "Listo";
      timerBig.textContent = "00:00";
    }

    roundLabel.textContent = (phase === "recovery" || phase === "done")
      ? String(seq.length)
      : String(Math.min(idx + 1, seq.length));

    renderQueue();
    setUIState();
  }

  function stop() {
    running = false;
    if (interval) clearInterval(interval);
    interval = null;
    setUIState();
  }

  function tick() {
    if (!running) return;

    remaining -= 1;
    timerBig.textContent = mmss(remaining);

    if (remaining <= 0) {
      if (phase === "work") {
        if (config.rest > 0) {
          setPhase("rest", config.rest);
        } else {
          idx += 1;
          if (idx >= seq.length) {
            if (config.recovery > 0) setPhase("recovery", config.recovery);
            else { setPhase("done", 0); stop(); }
          } else {
            loadExercise(idx);
            setPhase("work", config.work);
          }
        }
      } else if (phase === "rest") {
        idx += 1;
        if (idx >= seq.length) {
          if (config.recovery > 0) setPhase("recovery", config.recovery);
          else { setPhase("done", 0); stop(); }
        } else {
          loadExercise(idx);
          setPhase("work", config.work);
        }
      } else if (phase === "recovery") {
        setPhase("done", 0);
        stop();
      }
    }
  }

  function start() {
    if (running) return;
    running = true;

    if (phase === "idle") {
      idx = 0;
      loadExercise(idx);
      setPhase("work", config.work);
    }

    interval = setInterval(tick, 1000);
    setUIState();
  }

  function pause() {
    if (!running) return;
    running = false;
    if (interval) clearInterval(interval);
    interval = null;
    setUIState();
  }

  function reset() {
    stop();
    idx = 0;
    seq = getSeq();
    roundTotal.textContent = String(seq.length);
    loadExercise(0);
    setPhase("idle", 0);
  }

  btnApply.addEventListener("click", () => {
    sanitizeConfig();
    seq = getSeq();
    roundTotal.textContent = String(seq.length);
    reset();
  });

  btnStart.addEventListener("click", start);
  btnPause.addEventListener("click", pause);
  btnReset.addEventListener("click", reset);

  // init
  sanitizeConfig();
  seq = getSeq();
  roundTotal.textContent = String(seq.length);
  loadExercise(0);
  setPhase("idle", 0);
})();
