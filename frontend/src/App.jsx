import { useCallback, useEffect, useState } from "react";
import { BarChart3, FileText, MessageSquareWarning, Network, PhoneCall, ShieldCheck, Swords } from "lucide-react";
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
import Intel from "./pages/Intel";
import Check from "./pages/Check";
import Guardian from "./pages/Guardian";
import { DEMO } from "./demo";
import DemoBanner from "./demo/DemoBanner";

const NAV = [
  { group: "Scam line", items: [
    { to: "/app", label: "Live call", short: "Call", icon: PhoneCall, exact: true },
    { to: "/app/guardian", label: "Guardian (protect an elder)", short: "Guardian", icon: ShieldCheck },
    { to: "/app/check", label: "Check a message", short: "Check", icon: MessageSquareWarning },
    { to: "/app/history", label: "Calls & reports", short: "Reports", icon: FileText },
    { to: "/app/intel", label: "Scam intelligence", short: "Intel", icon: BarChart3 },
    { to: "/app/rings", label: "Scam ring radar", short: "Rings", icon: Network },
  ] },
  { group: "Testing", items: [
    { to: "/app/arena", label: "AI-vs-AI arena", short: "Arena", icon: Swords },
  ] },
];
const MOBILE_TABS = NAV.flatMap((g) => g.items).filter((i) => ["/app", "/app/guardian", "/app/check", "/app/intel", "/app/rings"].includes(i.to));
const TITLES = [
  ["/app/report", "Complaint report", "Draft for cybercrime.gov.in / 1930"],
  ["/app/history", "Calls & reports", "Every call Dadi took"],
  ["/app/check", "Check a message", "SMS, WhatsApp or 'notice'"],
  ["/app/guardian", "Guardian", "Protects a real elder on her own call"],
  ["/app/intel", "Scam intelligence", "For banks, telcos and police"],
  ["/app/rings", "Scam ring radar", "Same mule ID or same voice = same gang"],
  ["/app/arena", "AI-vs-AI arena", "Noisy phone line stress test"],
  ["/app", "Live scam line", "Gnani Prisma + Timbre"],
];

// [tone, full text, short text for phones, tooltip]
function healthState(h) {
  if (!h) return ["muted", "Server offline", "Offline"];
  if (h.demo) return ["cyan", "Demo · recorded on Gnani live", "Demo replay", "Replays calls recorded on Gnani's live servers: no server, no API keys"];
  if (h.fake) return ["amber", "Fake mode: no API keys", "Fake mode"];
  if (!h.gnani_key || !h.llm_key) return ["rose", "API keys missing", "Keys missing"];
  if (h.llm_ready === false && h.llm_last_error) return ["amber", "LLM error", "LLM error", `LLM error: ${h.llm_last_error}`];
  if (!h.fillers_ready) return ["cyan", "Warming up voices…", "Warming up…"];
  const model = h.llm_model || [h.llm_provider, h.llm_provider === "groq" ? h.groq_model : null].filter(Boolean).join(" ") || "LLM";
  return ["green", `Gnani live · ${model}`, "Gnani live"];
}

function HealthPill({ health }) {
  const [tone, text, short, tip = text] = healthState(health);
  return (
    <span className="health-pill" title={tip} role="status" aria-label={tip}>
      <Badge tone={tone} dot><span className="long">{text}</span><span className="short">{short}</span></Badge>
    </span>
  );
}

export default function App() {
  const route = useRoute();

  const { data: health, reload: reloadHealth } = useApi("/api/health");
  const { data: personas } = useApi("/api/personas");
  const [totals, setTotals] = useState(null);
  const refreshTotals = useCallback(() => { getJSON("/api/totals").then(setTotals).catch(() => {}); }, []);
  useEffect(refreshTotals, [refreshTotals]);
  // keep the pill honest: poll every 10 s (every 3 s while the voices warm up), also while the server is offline
  const warming = !!health && !health.fake && !health.fillers_ready;
  useEffect(() => {
    if (DEMO) return undefined; // static snapshot: nothing changes
    const id = setInterval(() => { if (!document.hidden) reloadHealth(); }, warming ? 3000 : 10000);
    return () => clearInterval(id);
  }, [warming, reloadHealth]);

  const call = useCall({ onEnded: refreshTotals });
  const [personaKey, setPersonaKey] = useState("auto");
  const [noise, setNoise] = useState("off");

  let page;
  if (route.path === "/app/report") page = <Report query={route.query} key={route.query?.id} />;
  else if (route.path === "/app/history") page = <History />;
  else if (route.path === "/app/arena") page = <Arena />;
  else if (route.path === "/app/rings") page = <Rings />;
  else if (route.path === "/app/intel") page = <Intel />;
  else if (route.path === "/app/check") page = <Check />;
  else if (route.path === "/app/guardian") page = <Guardian />;
  else page = (
    <CallRoom call={call} personas={personas || []} totals={totals} personaKey={personaKey} setPersonaKey={setPersonaKey} noise={noise} setNoise={setNoise} />
  );

  return (
    <>
      <AppShell
        path={route.path}
        brand={{ name: "Dadi vs Scammers", sub: "AI scam-baiter · Gnani", logo: "/icons/mark.svg", href: "#/app" }}
        nav={NAV}
        mobileTabs={MOBILE_TABS}
        titles={TITLES}
        topRight={<HealthPill health={health} />}
        banner={DEMO ? <DemoBanner /> : null}
        footer={<div className="pill-src">Built on Gnani AI: Prisma v3.0 (STT) · Timbre v3.0 (TTS) · Evon v3.3 (LLM, when hosted)</div>}
      >
        {page}
      </AppShell>
      <Toasts />
    </>
  );
}
