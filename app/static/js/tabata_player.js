// app/static/js/tabata_player.js
(function () {
  const data = window.TABATA_DATA || {};
  const cfg = data.cfg || {};
  const items = Array.isArray(data.items) ? data.items : [];

  const $ = (id) => document.getElementById(id);

  const els = {
    btnStart: $("btnStart"),
    btnPause: $("btnPause"),
    btnStop: $("btnStop"),
    timer: $("timer"),
    phaseLabel: $("phaseLabel"),
    exerciseLabel: $("exerciseLabel"),
    roundLabel: $("roundLabel"),
    nextLabel: $("nextLabel"),
    tabTitle: $("tabTitle"),
    tabSubtitle: $("tabSubtitle"),
    video: $("videoPlayer"),
  };

  const state = {
    running: false,
    paused: false,
    interval: null,
    phase: "idle", // idle | count_in | work | rest | recovery | done
    t: 0,
    idx: 0,
    round: 1,

    totalRounds: Number(cfg.rounds || 1),
    work: Number(cfg.work || 40),
    rest: Number(cfg.rest || 20),
    recovery: Number(cfg.recovery || 60),
    countIn: Number(cfg.count_in || 0),

    lastBeepAt: null,
    beepEnabled: true,
    audioReady: false,
    audioCtx: null,
  };

  // =========================
  // UTIL
  // =========================
  function pad2(n) {
    n = Math.max(0, parseInt(n || 0, 10));
    return n < 10 ? `0${n}` : `${n}`;
  }

  function setTimer(v) {
    els.timer.textContent = pad2(v);
  }

  function setPhase(text) {
    els.phaseLabel.textContent = text;
  }

  function currentItem() {
    if (!items.length) return null;
    const i = state.idx % items.length;
    return items[i];
  }

  function nextItemName() {
    if (!items.length) return "—";
    const nextIdx = (state.idx + 1) % items.length;
    const it = items[nextIdx];
    return it?.nombre || "Ejercicio";
  }

  function setExerciseUI() {
    const it = currentItem();
    if (!it) {
      els.exerciseLabel.textContent = "—";
      els.roundLabel.textContent = "—";
      els.nextLabel.textContent = "Agregá ejercicios en el Builder";
      return;
    }
    els.exerciseLabel.textContent = it.nombre || "Ejercicio";
    els.roundLabel.textContent = `${state.round} / ${state.totalRounds}`;
  }

  function enableControls(running) {
    els.btnStart.disabled = running;
    els.btnPause.disabled = !running;
    els.btnStop.disabled = !running;
  }

  function stopInterval() {
    if (state.interval) {
      clearInterval(state.interval);
      state.interval = null;
    }
  }

  // =========================
  // AUDIO (BEEPS)
  // =========================
  function ensureAudioContext() {
    if (state.audioCtx) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    state.audioCtx = new AC();
  }

  function resumeAudioIfNeeded() {
    if (!state.audioCtx) return;
    if (state.audioCtx.state === "suspended") {
      state.audioCtx.resume().catch(() => {});
    }
  }

  function beepOnce(freq = 880, durationMs = 90, gainVal = 0.08) {
    if (!state.beepEnabled) return;
    ensureAudioContext();
    if (!state.audioCtx) return;

    resumeAudioIfNeeded();

    const ctx = state.audioCtx;
    const o = ctx.createOscillator();
    const g = ctx.createGain();

    o.type = "sine";
    o.frequency.value = freq;

    const now = ctx.currentTime;
    g.gain.setValueAtTime(0.0001, now);
    g.gain.exponentialRampToValueAtTime(gainVal, now + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, now + durationMs / 1000);

    o.connect(g);
    g.connect(ctx.destination);

    o.start(now);
    o.stop(now + durationMs / 1000 + 0.02);
  }

  // 3..2..1 => pi - pii - ppiii
  function beepCountdown(t) {
    // t es el "segundos restantes" que se muestra
    // queremos sonar cuando t = 3, 2, 1
    if (![3, 2, 1].includes(t)) return;

    // evitar repetir si tick doble / cambios
    if (state.lastBeepAt === `${state.phase}:${t}:${state.idx}:${state.round}`) return;
    state.lastBeepAt = `${state.phase}:${t}:${state.idx}:${state.round}`;

    if (t === 3) beepOnce(740, 90, 0.07);
    if (t === 2) beepOnce(880, 110, 0.08);
    if (t === 1) beepOnce(1040, 140, 0.09);
  }

  function markAudioReady() {
    state.audioReady = true;
    // crear ctx desde gesto del usuario (click) para que iOS permita sonido
    ensureAudioContext();
    resumeAudioIfNeeded();
    // un beep MUY suave opcional (comentado)
    // beepOnce(440, 50, 0.02);
  }

  // =========================
  // VIDEO LOOP (work)
  // =========================
  function applyVideoLoopForWork() {
    const v = els.video;
    if (!v) return;

    // En work: loop ON
    v.loop = true;

    // iOS: playsinline + muted ayudan a autoplay
    v.muted = true;
    v.playsInline = true;

    // Si el video termina, loop debería reiniciar, pero algunos browsers fallan:
    // fuerza restart en ended.
    v.onended = () => {
      // si seguimos en work y corriendo, reiniciamos
      if (state.running && !state.paused && state.phase === "work") {
        try {
          v.currentTime = 0;
          v.play().catch(() => {});
        } catch (e) {}
      }
    };
  }

  function applyVideoNoLoopForRest() {
    const v = els.video;
    if (!v) return;
    // En descanso: lo pausamos y loop OFF
    v.loop = false;
    try { v.pause(); } catch (e) {}
  }

  function loadVideoForCurrent() {
    const it = currentItem();
    if (!it) return;

    const src = (it.video_src || "").trim();
    const v = els.video;

    if (!v) return;

    if (!src) {
      try { v.pause(); } catch (e) {}
      v.removeAttribute("src");
      v.load();
      return;
    }

    // Si ya es el mismo src, no recargues (evita parpadeo)
    const currentSrc = (v.getAttribute("src") || "").trim();
    if (currentSrc !== src) {
      try { v.pause(); } catch (e) {}
      v.setAttribute("src", src);
      v.load();
    }

    applyVideoLoopForWork();

    // Intentar play (si el browser bloquea, el usuario puede tocar play)
    setTimeout(() => {
      if (state.running && !state.paused && state.phase === "work") {
        try {
          v.play().catch(() => {});
        } catch (e) {}
      }
    }, 120);
  }

  function preview(index0) {
    if (!items.length) return;
    state.idx = Math.max(0, parseInt(index0, 10) || 0);
    setExerciseUI();
    loadVideoForCurrent();
  }

  // =========================
  // FLOW
  // =========================
  function reset() {
    stopInterval();
    state.running = false;
    state.paused = false;
    state.phase = "idle";
    state.t = 0;
    state.idx = 0;
    state.round = 1;
    state.lastBeepAt = null;

    enableControls(false);
    setPhase("Listo");
    setTimer(state.work);
    setExerciseUI();
    els.nextLabel.textContent = "—";

    const v = els.video;
    if (v) {
      try { v.pause(); } catch (e) {}
      // mantener src cargado para preview
    }

    if (els.btnPause) {
      els.btnPause.innerHTML = '<i class="bi bi-pause-fill"></i> Pausa';
    }
  }

  function advanceExercise() {
    state.idx += 1;
    if (items.length && state.idx % items.length === 0) {
      state.round += 1;
    }
  }

  function finish() {
    stopInterval();
    state.running = false;
    state.paused = false;
    state.phase = "done";
    enableControls(false);
    setPhase("🎉 Finalizado");
    setTimer(0);
    els.exerciseLabel.textContent = "—";
    els.roundLabel.textContent = "—";
    els.nextLabel.textContent = "Buen trabajo 💪";

    const v = els.video;
    if (v) {
      v.loop = false;
      try { v.pause(); } catch (e) {}
    }
  }

  function nextPhase() {
    // count_in -> work -> rest -> work ... -> recovery -> done

    if (state.phase === "count_in") {
      state.phase = "work";
      state.t = state.work;
      setPhase("💪 Trabaja");
      setExerciseUI();
      loadVideoForCurrent();
      els.nextLabel.textContent = state.rest > 0 ? `Luego: descanso ${state.rest}s` : `Luego: ${nextItemName()}`;
      return;
    }

    if (state.phase === "work") {
      // al terminar work vamos a rest o directo a siguiente / fin
      if (state.rest > 0) {
        state.phase = "rest";
        state.t = state.rest;
        setPhase("🧘 Descansa");
        applyVideoNoLoopForRest();
        els.nextLabel.textContent = `Luego: ${nextItemName()}`;
        return;
      }

      // sin descanso
      advanceExercise();
      if (state.round > state.totalRounds) {
        if (state.recovery > 0) {
          state.phase = "recovery";
          state.t = state.recovery;
          setPhase("🧊 Recuperación");
          applyVideoNoLoopForRest();
          els.nextLabel.textContent = "Finalizando…";
        } else {
          finish();
        }
      } else {
        state.phase = "work";
        state.t = state.work;
        setPhase("💪 Trabaja");
        setExerciseUI();
        loadVideoForCurrent();
        els.nextLabel.textContent = state.rest > 0 ? `Luego: descanso ${state.rest}s` : `Luego: ${nextItemName()}`;
      }
      return;
    }

    if (state.phase === "rest") {
      advanceExercise();
      if (state.round > state.totalRounds) {
        if (state.recovery > 0) {
          state.phase = "recovery";
          state.t = state.recovery;
          setPhase("🧊 Recuperación");
          applyVideoNoLoopForRest();
          els.nextLabel.textContent = "Finalizando…";
        } else {
          finish();
        }
      } else {
        state.phase = "work";
        state.t = state.work;
        setPhase("💪 Trabaja");
        setExerciseUI();
        loadVideoForCurrent();
        els.nextLabel.textContent = state.rest > 0 ? `Luego: descanso ${state.rest}s` : `Luego: ${nextItemName()}`;
      }
      return;
    }

    if (state.phase === "recovery") {
      finish();
    }
  }

  function tick() {
    if (!state.running || state.paused) return;

    // beep en 3..2..1 del tiempo RESTANTE (antes de bajar a 0)
    // (Cuando state.t es 3,2,1 sonará)
    beepCountdown(state.t);

    if (state.t <= 0) {
      nextPhase();
      return;
    }

    state.t -= 1;
    setTimer(state.t);
  }

  function start() {
    if (!items.length) {
      alert("Esta rutina no tiene ejercicios. Andá al Builder y agregalos.");
      return;
    }

    // activar audio desde gesto de usuario
    markAudioReady();

    state.running = true;
    state.paused = false;
    state.lastBeepAt = null;
    enableControls(true);

    if (state.countIn > 0) {
      state.phase = "count_in";
      state.t = state.countIn;
      setPhase("⏱️ Preparado");
      setExerciseUI();
      // En count-in no queremos video corriendo (opcional)
      applyVideoNoLoopForRest();
      els.nextLabel.textContent = `Luego: ${currentItem()?.nombre || "Ejercicio"} (${state.work}s)`;
      setTimer(state.t);
    } else {
      state.phase = "work";
      state.t = state.work;
      setPhase("💪 Trabaja");
      setExerciseUI();
      loadVideoForCurrent();
      els.nextLabel.textContent = state.rest > 0 ? `Luego: descanso ${state.rest}s` : `Luego: ${nextItemName()}`;
      setTimer(state.t);
    }

    stopInterval();
    state.interval = setInterval(tick, 1000);
  }

  function togglePause() {
    if (!state.running) return;

    // gesto del usuario => permite audio también
    markAudioReady();

    state.paused = !state.paused;

    if (els.btnPause) {
      els.btnPause.innerHTML = state.paused
        ? '<i class="bi bi-play-fill"></i> Reanudar'
        : '<i class="bi bi-pause-fill"></i> Pausa';
    }

    if (state.paused) {
      setPhase("⏸️ Pausado");
      const v = els.video;
      if (v) {
        try { v.pause(); } catch (e) {}
      }
      return;
    }

    // reanudar: si estamos en work, play video
    if (state.phase === "work") {
      setPhase("💪 Trabaja");
      const v = els.video;
      if (v) {
        applyVideoLoopForWork();
        try { v.play().catch(() => {}); } catch (e) {}
      }
    } else if (state.phase === "rest") {
      setPhase("🧘 Descansa");
      applyVideoNoLoopForRest();
    } else if (state.phase === "count_in") {
      setPhase("⏱️ Preparado");
    } else if (state.phase === "recovery") {
      setPhase("🧊 Recuperación");
    }
  }

  // Exponemos preview para tu button onclick="TabataUI.preview(i)"
  window.TabataUI = { preview, reset };

  // =========================
  // INIT
  // =========================
  if (els.tabTitle) els.tabTitle.textContent = cfg.title || "Tabata";

  if (els.tabSubtitle) {
    els.tabSubtitle.textContent =
      `${state.work}s trabajo · ${state.rest}s descanso · ${state.totalRounds} ronda(s) · recup ${state.recovery}s`;
  }

  // Preparar el video (mute + inline)
  if (els.video) {
    els.video.muted = true;
    els.video.playsInline = true;
    els.video.setAttribute("playsinline", "");
    els.video.setAttribute("webkit-playsinline", "");
  }

  // Listeners
  els.btnStart?.addEventListener("click", start);
  els.btnPause?.addEventListener("click", togglePause);
  els.btnStop?.addEventListener("click", reset);

  // iOS: tocar el video también “habilita” audio
  els.video?.addEventListener("click", () => markAudioReady());

  reset();
})();
