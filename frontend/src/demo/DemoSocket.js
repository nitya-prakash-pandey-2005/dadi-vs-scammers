// Replays a recorded WebSocket session with the browser WebSocket interface the UI already uses
// (readyState, onopen/onmessage/onerror/onclose, send, close), so callSocket.js and the arena need no other change.
//
// Timeline files (public/demo): [{ "t": seconds, "msg": { "type": ... } }, ...], replayed at real-time pace.
// Also accepted: { "events": [...] }, "data"/"message" instead of "msg", msg as a JSON string, epoch or ms times.
//   /ws/call  + {type:"start"}     -> ws-call.json   (the call audio, call.wav, is played by demoPlayer.js)
//   /ws/call  + {type:"start", replay:"family"} -> ws-family.json (audio: call-family.wav)
//   /ws/arena + {type:"arena"}     -> ws-arena.json
//   /ws/arena + {type:"benchmark"} -> ws-bench.json  (only if recorded)
import { hasDemoFile } from "./index.js";

const FILES = { start: "/demo/ws-call.json", arena: "/demo/ws-arena.json", benchmark: "/demo/ws-bench.json" };
const FAMILY_FILE = "/demo/ws-family.json";

export function normaliseTimeline(raw) {
  const list = Array.isArray(raw) ? raw : raw?.events || raw?.timeline || raw?.messages || [];
  let out = list.map((e) => {
    let msg = e?.msg ?? e?.data ?? e?.message ?? e?.event ?? e;
    if (typeof msg === "string") {
      try { msg = JSON.parse(msg); } catch { return null; }
    }
    const t = Number(e?.t ?? e?.time ?? e?.ts ?? 0);
    return msg && typeof msg === "object" && typeof msg.type === "string" && Number.isFinite(t) ? { t, msg } : null;
  }).filter(Boolean);
  if (!out.length) return out;
  const first = Math.min(...out.map((e) => e.t));
  if (first > 1e6) out = out.map((e) => ({ ...e, t: e.t - first })); // absolute (epoch) times
  const span = Math.max(...out.map((e) => e.t));
  if (span > 7200) out = out.map((e) => ({ ...e, t: e.t / 1000 })); // milliseconds
  return out.sort((a, b) => a.t - b.t);
}

// The arena emits each turn as soon as it is computed (fast or slow, depending on the network), so a recording of it
// flashes by or stalls. Replay it at a reading pace: each turn 2.5 to 4 s after the previous one (longer text, longer
// gap); intel, mission and repeat-caller messages follow the turn before them within 1.2 s, in their recorded order.
export function paceArena(events) {
  let lastOrig = null;
  let lastNew = 1.2; // the first line takes a moment, like a real call connecting
  return events.map((e) => {
    if (e.msg.type === "arena_turn") {
      if (lastOrig != null) lastNew += Math.min(4, 2.5 + String(e.msg.text || "").length / 80);
      lastOrig = e.t;
      return { ...e, t: lastNew };
    }
    return { ...e, t: lastOrig == null ? e.t : lastNew + Math.min(1.2, Math.max(0, e.t - lastOrig)) };
  });
}

export class DemoSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url) {
    this.url = url;
    this.kind = new URL(url, window.location.href).pathname; // "/ws/call" | "/ws/arena"
    this.readyState = 0;
    this.bufferedAmount = 0;
    this.binaryType = "blob";
    this.onopen = this.onmessage = this.onerror = this.onclose = null;
    this.timers = [];
    this.events = null;
    this.t0 = 0;
    this.timers.push(setTimeout(() => { // a short "ringing" moment, like a real connect
      if (this.readyState !== 0) return;
      this.readyState = 1;
      this.onopen?.({ type: "open" });
    }, 250));
  }

  send(data) {
    if (this.readyState !== 1 || typeof data !== "string") return; // mic audio: nobody listens in a replay
    let m;
    try { m = JSON.parse(data); } catch { return; }
    if (FILES[m.type] && !this.events) this.play(m.type, m.replay);
    else if (m.type === "hangup") this.hangup();
    // set_noise etc.: the recording can't change, so it is ignored
  }

  async play(kind, replay) {
    this.events = [];
    const file = kind === "start" && replay === "family" ? FAMILY_FILE : FILES[kind];
    let events = [];
    try {
      if (!hasDemoFile(file)) throw new Error("missing");
      const r = await fetch(file);
      if (!r.ok) throw new Error(String(r.status));
      events = normaliseTimeline(await r.json());
    } catch { /* handled below */ }
    if (this.readyState !== 1) return;
    if (!events.length) {
      this.emit(this.kind === "/ws/call"
        ? { type: "status", stt: "error", message: "This demo build has no recorded call" }
        : { type: "error", message: "This demo build has no recording for that run" });
      this.finish();
      return;
    }
    const started = events.find((e) => e.msg.type === "session_started")?.msg;
    if (kind === "start" && started && !events.some((e) => e.msg.type === "call_ended")) {
      // a capture cut before the hang-up: end it the way the server does
      const t = events[events.length - 1].t + 1;
      events.push({ t, msg: { type: "call_ended", call_id: started.call_id, wasted_seconds: Math.round(t * 10) / 10 } });
    }
    if (kind === "arena") events = paceArena(events);
    this.events = events;
    this.t0 = performance.now();
    for (const e of events) this.timers.push(setTimeout(() => this.emit(e.msg), e.t * 1000));
    // the server closes the socket right after the last message (call_ended / arena_done)
    this.timers.push(setTimeout(() => this.finish(), events[events.length - 1].t * 1000 + 300));
  }

  // Hang-up mid-replay: like the server, answer with call_ended for this call, then close.
  hangup() {
    this.clearTimers();
    const ended = [...(this.events || [])].reverse().find((e) => e.msg.type === "call_ended")?.msg;
    const started = (this.events || []).find((e) => e.msg.type === "session_started")?.msg;
    const elapsed = this.t0 ? (performance.now() - this.t0) / 1000 : 0;
    const callId = ended?.call_id || started?.call_id;
    this.timers.push(setTimeout(() => {
      if (callId) this.emit({ type: "call_ended", call_id: callId, wasted_seconds: Math.round(elapsed * 10) / 10 });
      this.finish();
    }, 300));
  }

  emit(msg) {
    if (this.readyState === 1) this.onmessage?.({ data: JSON.stringify(msg) });
  }

  clearTimers() {
    this.timers.forEach(clearTimeout);
    this.timers = [];
  }

  finish() {
    if (this.readyState === 3) return;
    this.clearTimers();
    this.readyState = 3;
    setTimeout(() => this.onclose?.({ type: "close", code: 1000 }), 0);
  }

  close() {
    this.finish();
  }
}
