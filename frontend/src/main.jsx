import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/inter";
import "@fontsource-variable/space-grotesk";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource/noto-sans-devanagari/400.css";
import "@fontsource/noto-sans-tamil/400.css";
import "@fontsource/noto-sans-bengali/400.css";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";
import "./styles/layout.css";
import "./styles/tour.css";
import "./app.css";
import "./wide.css";
import "./motion";
import { applySavedTheme } from "./lib/theme";
import Root from "./Root";
import { DEMO } from "./demo";

applySavedTheme();
// the service worker reloads stale tabs with ?sw=<build>; drop it so the address bar stays clean
if (new URLSearchParams(window.location.search).has("sw")) {
  window.history.replaceState(null, "", window.location.pathname + window.location.hash);
}
// the demo build (static hosting) has no service worker, so every redeploy shows up at once
if (DEMO && "serviceWorker" in navigator) {
  navigator.serviceWorker.getRegistrations().then((rs) => rs.forEach((r) => r.unregister())).catch(() => {});
} else if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" }).catch(() => {}));
}
createRoot(document.getElementById("root")).render(<StrictMode><Root /></StrictMode>);
