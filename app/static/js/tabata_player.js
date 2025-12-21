(function () {
  const data = window.TABATA_DATA || { cfg: {}, items: [] };
  const cfg = data.cfg || {};
  const items = Array.isArray(data.items) ? data.items : [];

  const $ = (id) => document.getElementById(id);

  const elTimer = $("timer");
  const elPhase = $("phaseLabel");
  const elEx = $("exerciseLabel");
  const elRound = $("roundLabel");
  const elNext = $("nextLabel");
  const video = $("videoPlayer");

  const btnStart = $("btnStart");
  const btnPause = $("btnPause");
  const btnStop = $("btnStop");

  let interval = null;
  let paused = false;

  let phase = "READY";
  let round = 1;
  let idx = 0;
  let secondsLeft = 0;

  const totalRounds = Math.max(1, parseInt(cfg.rounds || 1, 10));
  const WORK = Math.max(5, parseInt(cfg.work || 40, 10));
  const REST = Math.max(0, parseInt(cfg.rest || 20, 10));
  const RECOVERY = Math.max(0, parseInt(cfg.recovery || 60, 10));

  function fmt(n) {
    n = Math.max(0, n | 0);
    return String(n).padStart(2, "0");
  }

  function setButtons(running) {
    btnStart.disabled = running;
    btnPause.disabled = !running;
    btnStop.disabled = !running;
  }

  function currentItem() {
    return items[idx] || null;
  }

  function loadVideoForItem(it) {
    const src = (it && it.video_src) ? it.video_src : "";
    if (!src) {
      video.removeAttribute("src");
      video.load();
      return;
    }
    if (video.getAttribute("src") !== src) {
      video.setAttribute("src", src);
      video.load();
    }
  }

  function updateUI() {
    const it = currentItem();

    if (phase === "READY") {
      elPhase.innerText = "Listo";
      elEx.innerText = it ? it.nombre : "—";
      elTimer.innerText = fmt(WORK);
      elRound.innerText = items.length ? `${round} / ${totalRounds}` : "—";
      elNext.innerText = items.length ? "Dale play para arrancar" : "No hay ejercicios en esta rutina";
      return;
    }

    if (phase === "WORK") {
      elPhase.innerText = "💪 Trabajo";
      elEx.innerText = it ? it.nombre : "—";
      elTimer.innerText = fmt(secondsLeft);
      elRound.innerText = `${round} / ${totalRounds}`;
      elNext.innerText = `Luego: descanso ${REST}s`;
      return;
    }

    if (phase === "REST") {
      elPhase.innerText = "🧘 Descanso";
      elEx.innerText = it ? it.nombre : "—";
      elTimer.innerText = fmt(secondsLeft);
      elRound.innerText = `${round} / ${totalRounds}`;

      const nextIdx = (idx + 1 < items.length) ? (idx + 1) : 0;
      const nextRound = (idx + 1 < items.length) ? round : (round + 1);
      const nextIt = items[nextIdx];

      if (nextRound <= totalRounds && nextIt) {
        elNext.innerText = `Siguiente: ${nextIt.nombre} (${WORK}s)`;
      } else {
        elNext.innerText = RECOVERY > 0 ? `Luego: recuperación final ${RECOVERY}s` : "Luego: fin";
      }
      return;
    }

    if (phase === "RECOVERY") {
      elPhase.innerText = "🧊 Recuperación";
      elEx.innerText = "—";
      elTimer.innerText = fmt(secondsLeft);
      elRound.innerText = `${totalRounds} / ${totalRounds}`;
      elNext.innerText = "Cerrá con respiración y movilidad suave";
      return;
    }

    if (phase === "DONE") {
      elPhase.innerText = "🎉 Finalizado";
      elEx.innerText = "—";
      elTimer.innerText = "00";
      elRound.innerText = `${totalRounds} / ${totalRounds}`;
      elNext.innerText = "Buen trabajo.";
      return;
    }
  }

  function stopInterval(resetAll = true) {
    if (interval) clearInterval(interval);
    interval = null;
    paused = false;

    btnPause.innerHTML = '<i class="bi bi-pause-fill"></i> Pausa';

    if (resetAll) {
      phase = "READY";
      round = 1;
      idx = 0;
      secondsLeft = WORK;
      loadVideoForItem(currentItem());
      updateUI();
    }
    setButtons(false);
  }

  function advanceExerciseOrFinish() {
    idx += 1;

    if (idx >= items.length) {
      idx = 0;
      round += 1;
    }

    if (items.length === 0) {
      phase = "DONE";
      stopInterval(false);
      updateUI();
      return;
    }

    if (round > totalRounds) {
      if (RECOVERY > 0) {
        phase = "RECOVERY";
        secondsLeft = RECOVERY;
        loadVideoForItem(null);
        updateUI();
        return;
      }
      phase = "DONE";
      stopInterval(false);
      updateUI();
      return;
    }

    phase = "WORK";
    secondsLeft = WORK;
    loadVideoForItem(currentItem());
    updateUI();
  }

  function tick() {
    if (paused) return;

    secondsLeft -= 1;
    updateUI();

    if (secondsLeft > 0) return;

    if (phase === "WORK") {
      if (REST > 0) {
        phase = "REST";
        secondsLeft = REST;
        updateUI();
        return;
      }
      advanceExerciseOrFinish();
      return;
    }

    if (phase === "REST") {
      advanceExerciseOrFinish();
      return;
    }

    if (phase === "RECOVERY") {
      phase = "DONE";
      stopInterval(false);
      updateUI();
      return;
    }
  }

  function start() {
    if (!items.length) {
      alert("Esta rutina no tiene ejercicios. Agregalos en el Builder.");
      return;
    }

    paused = false;
    phase = "WORK";
    round = 1;
    idx = 0;
    secondsLeft = WORK;

    loadVideoForItem(currentItem());
    updateUI();

    setButtons(true);
    interval = setInterval(tick, 1000);
  }

  function pauseToggle() {
    if (!interval) return;
    paused = !paused;
    btnPause.innerHTML = paused
      ? '<i class="bi bi-play-fill"></i> Reanudar'
      : '<i class="bi bi-pause-fill"></i> Pausa';
  }

  window.TabataUI = {
    preview: function (i) {
      if (!items[i]) return;
      idx = i;
      loadVideoForItem(items[i]);
      elEx.innerText = items[i].nombre;
    }
  };

  btnStart.addEventListener("click", start);
  btnPause.addEventListener("click", pauseToggle);
  btnStop.addEventListener("click", function () { stopInterval(true); });

  stopInterval(true);
})();
