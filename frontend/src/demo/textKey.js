// Stable file key for a checker message (FNV-1a over the whitespace-normalised text).
// Shared by the demo build (src/demo/index.js) and the snapshot script (scripts/snapshot-demo.mjs).
export function textKey(text) {
  const s = String(text || "").trim().replace(/\s+/g, " ");
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}
