// Demo stand-in for the PCM player: plays the real call recording (stereo: left = scammer, right = Dadi) from t=0
// when the replayed call starts. Same interface as createPcmPlayer (play, flush, level, busy, close) plus start/stop.
// play/flush are no-ops: the recording already holds both sides, so a barge-in "stop_audio" must not cut it.
export function createDemoPlayer(src) {
  const audio = new Audio();
  audio.preload = "auto";
  audio.src = src;
  let ctx = null;
  let left = null;
  let right = null;
  try { // levels for the avatar ring; created inside the click, so the context may start
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    const node = ctx.createMediaElementSource(audio);
    const split = ctx.createChannelSplitter(2);
    left = ctx.createAnalyser();
    right = ctx.createAnalyser();
    left.fftSize = right.fftSize = 1024;
    node.connect(ctx.destination);
    node.connect(split);
    split.connect(left, 0);
    split.connect(right, 1);
  } catch {
    ctx = null; // plain <audio> playback still works
  }
  const scratch = new Float32Array(1024);
  const levelOf = (an) => {
    if (!an || audio.paused) return 0;
    an.getFloatTimeDomainData(scratch);
    let s = 0;
    for (let i = 0; i < scratch.length; i++) s += scratch[i] * scratch[i];
    return Math.min(1, Math.sqrt(s / scratch.length) * 6);
  };
  // the transcript runs on the wall clock from start(); if the file took a moment to load, jump the audio forward
  // once it plays, so voices and bubbles stay together
  let startedAt = 0;
  audio.addEventListener("playing", () => {
    const behind = (performance.now() - startedAt) / 1000 - audio.currentTime;
    if (startedAt && behind > 0.3 && Number.isFinite(audio.duration) && audio.currentTime + behind < audio.duration) {
      audio.currentTime += behind;
    }
    startedAt = 0; // only the first start
  });
  return {
    start() {
      startedAt = performance.now();
      ctx?.resume().catch(() => {});
      try { audio.currentTime = 0; } catch { /* not loaded yet: starts at 0 anyway */ }
      audio.play().catch(() => {});
    },
    stop() { audio.pause(); },
    play() {},
    flush() {},
    busy: () => !audio.paused,
    level: () => levelOf(right),
    callerLevel: () => levelOf(left),
    close() {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      ctx?.close().catch(() => {});
    },
  };
}
