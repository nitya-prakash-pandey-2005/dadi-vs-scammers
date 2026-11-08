import { useCallback, useEffect, useState } from "react";
import { FileText, Network, PhoneCall, Swords } from "lucide-react";
import { useRoute } from "./lib/router";
import AppShell from "./shell/AppShell";
import { Badge, Toasts } from "./ui";
import { getJSON, useApi } from "./lib/api";
import { useCall } from "./state/useCall";
import CallRoom from "./pages/CallRoom";
import History from "./pages/History";
import Report from "./pages/Report";
import Arena from "./pages/Arena";
import Rings from "./pages/Rings";

const NAV = [
  { group: "Scam line", items: [
    { to: "/app", label: "Live call", short: "Call", icon: PhoneCall, exact: true },
    { to: "/app/history", label: "Calls & reports", short: "Reports", icon: FileText },
    { to: "/app/rings", label: "Scam ring radar", short: "Rings", icon: Network },
  ] },
  { group: "Testing", items: [
    { to: "/app/arena", label: "AI-vs-AI arena", short: "Arena", icon: Swords },
  ] },
];
const TITLES = [
  ["/app/report", "Complaint report", "Draft for cybercrime.gov.in / 1930"],
  ["/app/history", "Calls & reports", "Every call Dadi took"],
  ["/app/rings", "Scam ring radar", "Same mule ID or same voice = same gang"],
  ["/app/arena", "AI-vs-AI arena", "Noisy phone line stress test"],
  ["/app", "Live scam line", "Gnani Prisma + Timbre"],
];

function HealthPill({ health }) {
  if (!health) return <Badge tone="muted" dot>Server offline</Badge>;
  if (health.fake) return <Badge tone="amber" dot>Fake mode: no API keys</Badge>;
  if (!health.gnani_key || !health.llm_key) return <Badge tone="rose" dot>API keys missing</Badge>;
  if (!health.fillers_ready) return <Badge tone="cyan" dot>Warming up voices…</Badge>;
  return <Badge tone="green" dot>Gnani live · {health.llm_provider}</Badge>;
}

export default function App() {
  const route = useRoute();
  useEffect(() => { if (route.path === "/" || route.path === "") window.location.hash = "/app"; }, [route.path]);

  const { data: health, reload: reloadHealth } = useApi("/api/health");
  const { data: personas } = useApi("/api/personas");
  const [totals, setTotals] = useState(null);
  const refreshTotals = useCallback(() => { getJSON("/api/totals").then(setTotals).catch(() => {}); }, []);
  useEffect(refreshTotals, [refreshTotals]);
  useEffect(() => {
    if (health && !health.fake && !health.fillers_ready) {
      const id = setTimeout(reloadHealth, 3000);
      return () => clearTimeout(id);
    }
    return undefined;
  }, [health, reloadHealth]);

  const call = useCall({ onEnded: refreshTotals });
  const [personaKey, setPersonaKey] = useState("auto");
  const [noise, setNoise] = useState("off");

  let page;
  if (route.path === "/app/report") page = <Report query={route.query} key={route.query?.id} />;
  else if (route.path === "/app/history") page = <History />;
  else if (route.path === "/app/arena") page = <Arena />;
  else if (route.path === "/app/rings") page = <Rings />;
  else page = (
    <CallRoom call={call} personas={personas || []} totals={totals} personaKey={personaKey} setPersonaKey={setPersonaKey} noise={noise} setNoise={setNoise} />
  );

  return (
    <>
      <AppShell
        path={route.path}
        brand={{ name: "Dadi vs Scammers", sub: "AI scam-baiter · Gnani", logo: "/icons/icon.svg", href: "#/app" }}
        nav={NAV}
        titles={TITLES}
        topRight={<HealthPill health={health} />}
        footer={<div className="pill-src">Built on Gnani AI: Prisma v3.0 (STT) · Timbre v3.0 (TTS) · Evon v3.3 (LLM, when hosted)</div>}
      >
        {page}
      </AppShell>
      <Toasts />
    </>
  );
}
