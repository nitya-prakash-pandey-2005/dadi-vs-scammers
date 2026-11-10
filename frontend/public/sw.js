// Offline-capable service worker.
// Pages are network-first (a rebuild shows up on the next load; the cached page is only the offline fallback).
// Hashed build assets are cache-first. /api and /ws are never touched.
const BUILD = "__DADI_BUILD__"; // replaced with a fresh id on every `npm run build` (vite.config.js)
const CACHE = `dadi-${BUILD}`;
const LEGACY = ["dadi-v1"]; // the old cache-first worker: pages it served are stale

const putCopy = (key, res) => {
  if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(key, copy)).catch(() => {}); }
  return res;
};

self.addEventListener("install", (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(["/", "/manifest.webmanifest"])).catch(() => {}));
});

self.addEventListener("activate", (e) => e.waitUntil((async () => {
  const stale = (await caches.keys()).filter((k) => k !== CACHE);
  await Promise.all(stale.map((k) => caches.delete(k)));
  await self.clients.claim();
  // a tab opened under the old cache-first worker is showing an old build: reload it once
  if (stale.some((k) => LEGACY.includes(k))) {
    const wins = await self.clients.matchAll({ type: "window" });
    await Promise.all(wins.map((w) => w.navigate(w.url).catch(() => null)));
  }
})()));

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api") || url.pathname.startsWith("/ws") || url.pathname === "/sw.js") return;

  if (req.mode === "navigate" || url.pathname === "/" || url.pathname === "/index.html") {
    e.respondWith(
      fetch(req, { cache: "no-cache" }) // revalidate: never a heuristically "fresh" old index.html
        .then((res) => putCopy("/", res))
        .catch(() => caches.match("/").then((hit) => hit || Response.error())),
    );
    return;
  }

  e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => putCopy(req, res))));
});
