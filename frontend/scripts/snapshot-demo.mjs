#!/usr/bin/env node
// Save every REST response the UI reads into frontend/public/demo/api/, so the demo build (npm run build:demo)
// can show them without a backend. Run it against a backend that only reads its database:
//
//   GNANI_API_KEY= GROQ_API_KEY= uv run python -m uvicorn dadi.app:create_app --factory --port 8765   (repo root)
//   cd frontend && npm run snapshot:demo -- --base http://127.0.0.1:8765
//
// Options
//   --base <url>        backend URL (default http://127.0.0.1:8765)
//   --no-audio          skip the call recordings (calls/<id>/audio.wav)
//   --no-evidence       skip the evidence packs (calls/<id>/evidence.zip)
//   --calls <id,id>     only these calls get recordings and evidence packs (all calls still get their report)
//   --capture-call <s>  ALSO record a <s>-second /ws/call session into public/demo/ws-call.json + call.wav
//   --capture-arena     ALSO record one /ws/arena run into public/demo/ws-arena.json
//                       (captures are for a fake-mode backend, DADI_FAKE=1: against a live one they spend credits)
// public/demo/api is replaced on every run; ws-*.json and call.wav next to it are only written by --capture-*.
import { mkdir, rm, writeFile, readdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { SAMPLES } from "../src/lib/checkSamples.js";
import { textKey } from "../src/demo/textKey.js";

const here = dirname(fileURLToPath(import.meta.url));
const DEMO = join(here, "..", "public", "demo");
const OUT = join(DEMO, "api");

const args = process.argv.slice(2);
const flag = (name) => args.includes(name);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 && args[i + 1] ? args[i + 1] : dflt; };
const BASE = opt("--base", "http://127.0.0.1:8765").replace(/\/$/, "");
const ONLY = opt("--calls", "") ? new Set(opt("--calls", "").split(",").map((s) => s.trim())) : null;

async function get(path, kind = "json") {
  const r = await fetch(BASE + path);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return kind === "json" ? r.json() : Buffer.from(await r.arrayBuffer());
}
async function save(rel, data) {
  const file = join(OUT, rel);
  await mkdir(dirname(file), { recursive: true });
  await writeFile(file, Buffer.isBuffer(data) ? data : JSON.stringify(data));
  return file;
}

async function snapshotRest() {
  await rm(OUT, { recursive: true, force: true });
  await mkdir(OUT, { recursive: true });

  const health = await get("/api/health");
  // the demo shows a "Demo replay" pill; drop anything that only describes this machine's server
  await save("health.json", { ...health, demo: true, llm_last_error: null, fake: false });
  for (const name of ["personas", "missions", "totals", "calls", "rings", "insights", "freeze-list"]) {
    await save(`${name}.json`, await get(`/api/${name}`));
  }
  await save("freeze-list.csv", await get("/api/freeze-list?format=csv", "bin"));
  await save("feed/mule-ids.csv", await get("/api/feed/mule-ids.csv", "bin"));
  await save("feed/mule-ids.json", await get("/api/feed/mule-ids.json"));

  const calls = await get("/api/calls");
  let audio = 0;
  for (const c of calls) {
    await save(`calls/${c.id}.json`, await get(`/api/calls/${c.id}`));
    const report = await get(`/api/calls/${c.id}/report`);
    await save(`calls/${c.id}/report.json`, report);
    const wanted = !ONLY || ONLY.has(c.id);
    if (wanted && report.recording && !flag("--no-audio")) {
      await save(`calls/${c.id}/audio.wav`, await get(`/api/calls/${c.id}/audio`, "bin"));
      audio += 1;
    }
    if (wanted && !flag("--no-evidence")) await save(`calls/${c.id}/evidence.zip`, await get(`/api/calls/${c.id}/evidence.zip`, "bin"));
  }
  console.log(`calls: ${calls.length} (recordings saved: ${audio})`);

  let checks = 0;
  for (const s of SAMPLES) {
    try {
      const r = await fetch(BASE + "/api/check", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: s.text }) });
      if (!r.ok) throw new Error(String(r.status));
      await save(`check/${textKey(s.text)}.json`, await r.json());
      checks += 1;
    } catch (e) {
      console.warn(`checker sample "${s.label}" not saved (${e.message}): the demo shows the "try a sample" note for it`);
    }
  }
  console.log(`checker samples: ${checks}/${SAMPLES.length}`);
}

// Record a WebSocket session as [{t, msg}] (binary frames are skipped: call audio comes from the recording).
function capture(path, first, { seconds = 0 } = {}) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(BASE.replace(/^http/, "ws") + path);
    const events = [];
    let t0 = 0;
    ws.onopen = () => { t0 = performance.now(); ws.send(JSON.stringify(first)); };
    ws.onmessage = (e) => {
      if (typeof e.data !== "string") return;
      events.push({ t: Math.round(performance.now() - t0) / 1000, msg: JSON.parse(e.data) });
    };
    ws.onerror = () => reject(new Error(`could not open ${path}`));
    ws.onclose = () => resolve(events);
    if (seconds) setTimeout(() => ws.send(JSON.stringify({ type: "hangup" })), seconds * 1000);
  });
}

async function captures() {
  const callSecs = Number(opt("--capture-call", 0));
  if (callSecs) {
    const events = await capture("/ws/call", { type: "start", persona: "auto", noise_snr_db: null, mission: null }, { seconds: callSecs });
    await writeFile(join(DEMO, "ws-call.json"), JSON.stringify(events, null, 1));
    const id = events.find((e) => e.msg.type === "call_ended")?.msg.call_id;
    if (id) {
      await new Promise((ok) => setTimeout(ok, 1500)); // the server saves the recording after call_ended
      await writeFile(join(DEMO, "call.wav"), await get(`/api/calls/${id}/audio`, "bin"));
    }
    console.log(`ws-call.json: ${events.length} events, call ${id || "?"}${id ? " + call.wav" : ""}`);
  }
  if (flag("--capture-arena")) {
    const events = await capture("/ws/arena", { type: "arena", scam_type: "digital_arrest", turns: 6, snr_db: 10, persona: "dadi", scammer_voice: "Harshad", mission: null });
    await writeFile(join(DEMO, "ws-arena.json"), JSON.stringify(events, null, 1));
    console.log(`ws-arena.json: ${events.length} events`);
  }
}

async function sizeOf(dir) {
  let n = 0;
  for (const e of await readdir(dir, { withFileTypes: true })) n += e.isDirectory() ? await sizeOf(join(dir, e.name)) : (await stat(join(dir, e.name))).size;
  return n;
}

try {
  await captures(); // first, so the snapshot includes the captured call
  await snapshotRest();
  console.log(`saved to ${DEMO} (${(await sizeOf(DEMO) / 1e6).toFixed(1)} MB). Now: npm run build:demo`);
} catch (e) {
  console.error(`snapshot failed: ${e.message}. Is the backend running at ${BASE}?`);
  process.exit(1);
}
