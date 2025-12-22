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
    lastPhase: null,
  };

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

  function loadVideoForCurrent() {
    const it = currentItem();
    if (!it) return;

    const src = (it.video_src || "").trim();
    if (!src) {
      // sin video, no rompemos
      try { els.video.pause(); } catch(e) {}
      els.video.removeAttribute("src");
      els.video.load();
      return;
    }

    try { els.video.pause(); } catch(e) {}
    els.video.src = src;
    els.video.load();
  }

  function preview(index0) {
    if (!items.length) return;
    state.idx = Math.max(0, parseInt(index0, 10) || 0);
    setExerciseUI();
    loadVideoForCurrent();
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

  function reset() {
    stopInterval();
    state.running = false;
    state.paused = false;
    state.phase = "idle";
    state.t = 0;
    state.idx = 0;
    state.round = 1;
    state.lastPhase = null;

    enableControls(false);
    setPhase("Listo");
    setTimer(state.work);
    setExerciseUI();
    els.nextLabel.textContent = "—";

    try { els.video.pause(); } catch(e) {}
  }

  function nextPhase() {
    // Secuencia:
    // count_in -> work -> rest -> work -> ... -> recovery -> done
    if (state.phase === "count_in") {
      state.phase = "work";
      state.t = state.work;
      state.lastPhase = "work";
      setPhase("💪 Trabaja");
      setExerciseUI();
      loadVideoForCurrent();
      els.nextLabel.textContent = `Luego: descanso ${state.rest}s`;
      return;
    }

    if (state.phase === "work") {
      // termina un work, pasamos a rest o a recovery/done
      if (state.rest > 0) {
        state.phase = "rest";
        state.t = state.rest;
        state.lastPhase = "rest";
        setPhase("🧘 Descansa");
        els.nextLabel.textContent = `Luego: ${nextExerciseName()}`;
      } else {
        // sin rest => avanzamos directamente a siguiente work o fin
        advanceExercise();
        if (state.round > state.totalRounds) {
          if (state.recovery > 0) {
            state.phase = "recovery";
            state.t = state.recovery;
            setPhase("🧊 Recuperación");
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
          els.nextLabel.textContent = state.rest > 0 ? `Luego: descanso ${state.rest}s` : `Luego: ${nextExerciseName()}`;
        }
      }
      return;
    }

    if (state.phase === "rest") {
      // terminamos descanso, avanzamos ejercicio + ronda
      advanceExercise();
      if (state.round > state.totalRounds) {
        if (state.recovery > 0) {
          state.phase = "recovery";
          state.t = state.recovery;
          setPhase("🧊 Recuperación");
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
        els.nextLabel.textContent = state.rest > 0 ? `Luego: descanso ${state.rest}s` : `Luego: ${nextExerciseName()}`;
      }
      return;
    }

    if (state.phase === "recovery") {
      finish();
      return;
    }
  }

  function nextExerciseName() {
    if (!items.length) return "—";
    const nextIdx = (state.idx + 1) % items.length;
    const it = items[nextIdx];
    return `Luego: ${it?.nombre || "Ejercicio"}`;
  }

  function advanceExercise() {
    state.idx += 1;
    // si completamos vuelta (idx múltiplo de items.length) subimos ronda
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
    try { els.video.pause(); } catch(e) {}
  }

  function tick() {
    if (!state.running || state.paused) return;

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

    state.running = true;
    state.paused = false;
    enableControls(true);

    // inicio: count_in opcional
    if (state.countIn > 0) {
      state.phase = "count_in";
      state.t = state.countIn;
      setPhase("⏱️ Preparado");
      els.nextLabel.textContent = `Luego: ${currentItem()?.nombre || "Ejercicio"} (${state.work}s)`;
      setExerciseUI();
      loadVideoForCurrent();
      setTimer(state.t);
    } else {
      state.phase = "work";
      state.t = state.work;
      setPhase("💪 Trabaja");
      setExerciseUI();
      loadVideoForCurrent();
      els.nextLabel.textContent = state.rest > 0 ? `Luego: descanso ${state.rest}s` : `Luego: ${nextExerciseName()}`;
      setTimer(state.t);
    }

    stopInterval();
    state.interval = setInterval(tick, 1000);
  }

  function togglePause() {
    if (!state.running) return;
    state.paused = !state.paused;
    els.btnPause.innerHTML = state.paused
      ? '<i class="bi bi-play-fill"></i> Reanudar'
      : '<i class="bi bi-pause-fill"></i> Pausa';
    setPhase(state.paused ? "⏸️ Pausado" : (state.phase === "rest" ? "🧘 Descansa" : "💪 Trabaja"));
  }

  // Exponemos preview para tu button onclick="TabataUI.preview(i)"
  window.TabataUI = {
    preview,
    reset,
  };

  // Init UI
  if (els.tabTitle) els.tabTitle.textContent = cfg.title || "Tabata";
  if (els.tabSubtitle) {
    els.tabSubtitle.textContent =
      `${state.work}s trabajo · ${state.rest}s descanso · ${state.totalRounds} ronda(s) · recup ${state.recovery}s`;
  }

  els.btnStart?.addEventListener("click", start);
  els.btnPause?.addEventListener("click", togglePause);
  els.btnStop?.addEventListener("click", reset);

  reset();
})();
