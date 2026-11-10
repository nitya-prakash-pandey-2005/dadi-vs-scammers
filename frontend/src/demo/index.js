// Demo build (VITE_DEMO=1, `npm run build:demo`): no backend. REST calls read static snapshots from public/demo/api,
// WebSockets replay recorded timelines (DemoSocket.js), and the call audio is the real recording (demoPlayer.js).
// A normal build never takes these paths (DEMO is false there).
import files from "virtual:demo-files";
import { textKey } from "./textKey.js";

export const DEMO = import.meta.env.VITE_DEMO === "1";
export const REPO_URL = "https://github.com/nitya-prakash-pandey-2005/dadi-vs-scammers";
export const RECORDED_ON = "10 Nov 2026";
export const DEMO_CALL_AUDIO = "/demo/call.wav";
export const NOT_IN_DEMO = "Not included in this demo build: run Dadi locally with your own keys for this";

const have = new Set(files); // "demo/api/calls.json", "demo/ws-call.json", ...
export const hasDemoFile = (p) => have.has(p.replace(/^\//, ""));

// "/api/calls/ab12/report" -> "/demo/api/calls/ab12/report.json"; "/api/freeze-list?format=csv" -> ".../freeze-list.csv"
export function demoPath(path) {
  const u = new URL(path, "http://demo.local");
  let p = u.pathname.replace(/^\/api\//, "");
  if (u.searchParams.get("format") === "csv") p += ".csv";
  else if (p.endsWith("/audio")) p += ".wav";
  else if (!/\.[a-z0-9]+$/i.test(p)) p += ".json";
  return `/demo/api/${p}`;
}

// Link target for a download or <audio>: the API path normally; in the demo the static copy, or null when the
// snapshot doesn't have it (the UI then shows the button disabled with a tooltip).
export function apiHref(path) {
  if (!DEMO || !path) return path;
  const p = demoPath(path);
  return hasDemoFile(p) ? p : null;
}

export async function demoGet(path) {
  const p = demoPath(path);
  if (path === "/api/health" && !hasDemoFile(p)) return { demo: true };
  if (!hasDemoFile(p)) throw new Error(`${path} → 404 (not in the demo snapshot)`);
  const r = await fetch(p, { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  const data = await r.json();
  return path === "/api/health" ? { ...data, demo: true } : data;
}

// POST /api/check: the recorded verdict for a sample message, or a note for any other text
export async function demoPost(path, body) {
  if (path !== "/api/check") throw new Error(`${path} is not available in the demo`);
  const p = `/demo/api/check/${textKey(body?.text)}.json`;
  if (hasDemoFile(p)) {
    const r = await fetch(p);
    if (r.ok) return r.json();
  }
  await new Promise((ok) => setTimeout(ok, 400)); // feels like a check, not an instant error
  return { demo_note: true };
}
