import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

const voiceWeb = fileURLToPath(new URL("../voice-core/web", import.meta.url));

export default defineConfig({
  plugins: [react()],
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
