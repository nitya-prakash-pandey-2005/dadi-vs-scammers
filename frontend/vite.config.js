import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { readFileSync, writeFileSync, existsSync, readdirSync, rmSync } from "node:fs";
import { join, relative } from "node:path";

const voiceWeb = fileURLToPath(new URL("../voice-core/web", import.meta.url));
const publicDemo = fileURLToPath(new URL("./public/demo", import.meta.url));

// Stamp a fresh build id into dist/sw.js, so every build gets its own cache and old ones are dropped.
function stampServiceWorker() {
  let outDir = "dist";
  return {
    name: "dadi-stamp-sw",
    apply: "build",
    configResolved(c) { outDir = c.build.outDir; },
    closeBundle() {
      const sw = join(outDir, "sw.js");
      if (!existsSync(sw)) return;
      const id = Date.now().toString(36);
      writeFileSync(sw, readFileSync(sw, "utf8").replace("__DADI_BUILD__", id));
    },
  };
}

// Demo build (`npm run build:demo`, VITE_DEMO=1): the app replays recorded data from public/demo instead of a backend.
// - `virtual:demo-files` lists the files in public/demo, so the UI can disable a download the snapshot doesn't have.
// - The normal build drops dist/demo again, so it stays exactly as it was (no recorded data shipped with it).
function demoData(isDemo) {
  const id = "virtual:demo-files";
  let outDir = "dist";
  const walk = (dir) => (existsSync(dir) ? readdirSync(dir, { withFileTypes: true }) : [])
    .flatMap((e) => (e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name)]));
  return {
    name: "dadi-demo-data",
    configResolved(c) { outDir = c.build.outDir; },
    resolveId(s) { return s === id ? "\0" + id : null; },
    load(s) {
      if (s !== "\0" + id) return null;
      const files = isDemo ? walk(publicDemo).map((f) => "demo/" + relative(publicDemo, f).split("\\").join("/")) : [];
      return `export default ${JSON.stringify(files)};`;
    },
    closeBundle() {
      if (!isDemo) rmSync(join(outDir, "demo"), { recursive: true, force: true });
    },
  };
}

export default defineConfig(({ mode }) => ({
  plugins: [react(), stampServiceWorker(), demoData(mode === "demo")],
  resolve: { alias: { "@voice": voiceWeb } },
  server: {
    port: 5191,
    fs: { allow: [".", voiceWeb] },
    proxy: {
      "/api": "http://127.0.0.1:8765",
      "/ws": { target: "ws://127.0.0.1:8765", ws: true },
    },
  },
  // emit the AudioWorklet as a real file (data: URLs are not accepted by addModule everywhere)
  build: { target: "es2022", assetsInlineLimit: (file) => (file.endsWith(".js") ? false : undefined) },
}));
