(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  const countdown = $("#countdown");
  const status = $("#status");
  const toggleButton = $("#toggleButton");
  const resetButton = $("#resetButton");
  const testButton = $("#testButton");
  const customSeconds = $("#customSeconds");
  const applyCustom = $("#applyCustom");
  const chimeCount = $("#chimeCount");
  const intervalLabel = $("#intervalLabel");
  const elapsed = $("#elapsed");
  const soundMode = $("#soundMode");
  const volume = $("#volume");
  const volumeValue = $("#volumeValue");
  const wakeLock = $("#wakeLock");
  const presets = $$(".preset");

  const state = {
    intervalMs: 30_000,
    running: false,
    nextDueAt: null,
    pausedRemainingMs: 30_000,
    startedAt: null,
    accumulatedElapsedMs: 0,
    count: 0,
    loopId: null,
    audioContext: null,
    wakeLockSentinel: null,
  };

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function formatDuration(ms, includeHours = false) {
    const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (includeHours || hours > 0) {
      return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    }
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  function getAudioContext() {
    if (!state.audioContext) {
      const Context = window.AudioContext || window.webkitAudioContext;
      if (!Context) return null;
      state.audioContext = new Context();
    }
    return state.audioContext;
  }

  async function ensureAudioReady() {
    const ctx = getAudioContext();
    if (ctx && ctx.state === "suspended") {
      try { await ctx.resume(); } catch (_) {}
    }
    return ctx;
  }

  function makeTone(ctx, destination, frequency, start, duration, level, type = "sine") {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(frequency, start);
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, level), start + 0.008);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    osc.connect(gain).connect(destination);
    osc.start(start);
    osc.stop(start + duration + 0.02);
  }

  async function playChime() {
    const ctx = await ensureAudioReady();
    if (!ctx) return;

    const master = ctx.createGain();
    const userVolume = Number(volume.value) / 100;
    master.gain.value = userVolume;
    master.connect(ctx.destination);

    const now = ctx.currentTime + 0.01;
    const mode = soundMode.value;

    if (mode === "click") {
      makeTone(ctx, master, 1080, now, 0.10, 0.34, "square");
      return;
    }

    if (mode === "soft") {
      makeTone(ctx, master, 660, now, 0.75, 0.18);
      makeTone(ctx, master, 990, now + 0.015, 0.90, 0.10);
      return;
    }

    makeTone(ctx, master, 880, now, 1.15, 0.22);
    makeTone(ctx, master, 1320, now + 0.012, 1.45, 0.12);
    makeTone(ctx, master, 1760, now + 0.018, 1.70, 0.06);
  }

  function setIntervalSeconds(seconds) {
    const safeSeconds = clamp(Math.round(Number(seconds) || 30), 5, 3600);
    state.intervalMs = safeSeconds * 1000;
    state.pausedRemainingMs = state.intervalMs;
    customSeconds.value = String(safeSeconds);
    intervalLabel.textContent = `${safeSeconds}s`;

    presets.forEach((button) => {
      const isPreset = Number(button.dataset.seconds) === safeSeconds;
      button.classList.toggle("is-active", isPreset);
      button.setAttribute("aria-pressed", isPreset ? "true" : "false");
    });

    if (state.running) {
      state.nextDueAt = performance.now() + state.intervalMs;
      status.textContent = `${safeSeconds}秒で再スタート`;
    } else {
      countdown.textContent = formatDuration(state.intervalMs);
    }

    localStorage.setItem("tokuChime.intervalSeconds", String(safeSeconds));
  }

  function getElapsedMs() {
    if (!state.running || state.startedAt === null) return state.accumulatedElapsedMs;
    return state.accumulatedElapsedMs + (performance.now() - state.startedAt);
  }

  function updateUI() {
    const now = performance.now();
    const remaining = state.running && state.nextDueAt !== null
      ? Math.max(0, state.nextDueAt - now)
      : state.pausedRemainingMs;

    countdown.textContent = formatDuration(remaining);
    elapsed.textContent = formatDuration(getElapsedMs(), false);
    chimeCount.textContent = String(state.count);
    document.title = state.running ? `${formatDuration(remaining)} · Toku Chime` : "Toku Chime — Tokumaru Labs";
  }

  async function tick() {
    if (!state.running || state.nextDueAt === null) return;
    const now = performance.now();

    if (now >= state.nextDueAt) {
      const behind = now - state.nextDueAt;
      const skippedIntervals = Math.floor(behind / state.intervalMs);
      state.count += 1;
      state.nextDueAt += (skippedIntervals + 1) * state.intervalMs;
      await playChime();
      status.textContent = skippedIntervals > 0 ? "遅延を補正して継続中" : "動作中";
    }

    updateUI();
  }

  function startLoop() {
    stopLoop();
    state.loopId = window.setInterval(tick, 80);
  }

  function stopLoop() {
    if (state.loopId !== null) {
      window.clearInterval(state.loopId);
      state.loopId = null;
    }
  }

  async function start() {
    await ensureAudioReady();
    if (state.running) return;

    const now = performance.now();
    state.running = true;
    state.startedAt = now;
    state.nextDueAt = now + clamp(state.pausedRemainingMs, 50, state.intervalMs);
    toggleButton.textContent = "PAUSE";
    toggleButton.classList.add("is-running");
    status.textContent = "動作中";
    startLoop();
    await syncWakeLock();
    updateUI();
  }

  async function pause() {
    if (!state.running) return;
    const now = performance.now();
    state.pausedRemainingMs = Math.max(0, state.nextDueAt - now);
    state.accumulatedElapsedMs += now - state.startedAt;
    state.running = false;
    state.startedAt = null;
    state.nextDueAt = null;
    toggleButton.textContent = "RESUME";
    toggleButton.classList.remove("is-running");
    status.textContent = "一時停止";
    stopLoop();
    await releaseWakeLock();
    updateUI();
  }

  async function reset() {
    stopLoop();
    state.running = false;
    state.nextDueAt = null;
    state.pausedRemainingMs = state.intervalMs;
    state.startedAt = null;
    state.accumulatedElapsedMs = 0;
    state.count = 0;
    toggleButton.textContent = "START";
    toggleButton.classList.remove("is-running");
    status.textContent = "停止中";
    await releaseWakeLock();
    updateUI();
  }

  async function toggle() {
    if (state.running) await pause();
    else await start();
  }

  async function requestWakeLock() {
    if (!wakeLock.checked || !("wakeLock" in navigator) || !state.running || document.visibilityState !== "visible") return;
    try {
      state.wakeLockSentinel = await navigator.wakeLock.request("screen");
      state.wakeLockSentinel.addEventListener("release", () => {
        state.wakeLockSentinel = null;
      });
    } catch (_) {
      wakeLock.checked = false;
    }
  }

  async function releaseWakeLock() {
    if (!state.wakeLockSentinel) return;
    try { await state.wakeLockSentinel.release(); } catch (_) {}
    state.wakeLockSentinel = null;
  }

  async function syncWakeLock() {
    if (wakeLock.checked) await requestWakeLock();
    else await releaseWakeLock();
  }

  presets.forEach((button) => {
    button.addEventListener("click", () => setIntervalSeconds(button.dataset.seconds));
  });

  applyCustom.addEventListener("click", () => setIntervalSeconds(customSeconds.value));
  customSeconds.addEventListener("keydown", (event) => {
    if (event.key === "Enter") setIntervalSeconds(customSeconds.value);
  });

  toggleButton.addEventListener("click", toggle);
  resetButton.addEventListener("click", reset);
  testButton.addEventListener("click", playChime);

  soundMode.addEventListener("change", () => localStorage.setItem("tokuChime.soundMode", soundMode.value));
  volume.addEventListener("input", () => {
    volumeValue.textContent = `${volume.value}%`;
    localStorage.setItem("tokuChime.volume", volume.value);
  });
  wakeLock.addEventListener("change", syncWakeLock);

  document.addEventListener("visibilitychange", async () => {
    if (document.visibilityState === "visible" && state.running && wakeLock.checked) {
      await requestWakeLock();
    }
  });

  document.addEventListener("keydown", async (event) => {
    const tag = event.target?.tagName?.toLowerCase();
    if (["input", "select", "textarea"].includes(tag)) return;

    if (event.code === "Space") {
      event.preventDefault();
      await toggle();
      return;
    }

    if (event.key === "1") setIntervalSeconds(30);
    if (event.key === "2") setIntervalSeconds(45);
    if (event.key === "3") setIntervalSeconds(60);
    if (event.key.toLowerCase() === "r") await reset();
    if (event.key.toLowerCase() === "t") await playChime();
  });

  window.addEventListener("beforeunload", releaseWakeLock);

  const savedInterval = Number(localStorage.getItem("tokuChime.intervalSeconds"));
  const savedVolume = Number(localStorage.getItem("tokuChime.volume"));
  const savedMode = localStorage.getItem("tokuChime.soundMode");

  if (Number.isFinite(savedVolume) && savedVolume >= 0 && savedVolume <= 100) {
    volume.value = String(savedVolume);
    volumeValue.textContent = `${savedVolume}%`;
  }
  if (["bell", "soft", "click"].includes(savedMode)) soundMode.value = savedMode;
  setIntervalSeconds(Number.isFinite(savedInterval) && savedInterval >= 5 ? savedInterval : 30);
  updateUI();
})();
