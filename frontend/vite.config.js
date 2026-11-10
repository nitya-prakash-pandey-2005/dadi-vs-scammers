import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const voiceWeb = fileURLToPath(new URL("../voice-core/web", import.meta.url));

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

export default defineConfig({
  plugins: [react(), stampServiceWorker()],
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
});
