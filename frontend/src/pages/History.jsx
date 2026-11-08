import { ChevronRight, Download, History as HistoryIcon } from "lucide-react";
import { Avatar, Badge, Card, PageHead } from "../ui";
import { useApi } from "../lib/api";
import { PERSONA_HUE, SCAM_TYPE_LABELS, identifierCount, mmss } from "../lib/labels";
import { Totals } from "../components/WarRoom";

const NAMES = { dadi: "Kamla Devi (Dadi)", paati: "Meenakshi (Paati)", thakuma: "Bela Rani (Thakuma)" };

export default function History() {
  const { data: calls, loading, error } = useApi("/api/calls");
  const { data: totals } = useApi("/api/totals");
  return (
    <>
      <PageHead
        kicker="Calls & reports"
        title="Every scam call Dadi took"
        sub="Open any call for its complaint draft, recording and evidence pack."
        right={<a className="btn sm" href="/api/feed/mule-ids.csv" download><Download size={15} /> Mule-ID feed for banks (CSV)</a>}
      />
      <div className="grid">
        <Totals totals={totals} />
        <Card icon={HistoryIcon} title="Calls" right={<Badge>{calls?.length ?? 0}</Badge>}>
          {loading && !calls && <div className="skeleton" style={{ height: 120 }} />}
          {error && <div className="empty">Could not load calls. Is the backend running?</div>}
          {calls && !calls.length && <div className="empty">No calls yet. Start one from “Live call”.</div>}
          <div className="list">
            {calls?.map((c) => {
              const n = identifierCount(c.intel);
              const type = c.intel?.scam_type || "other";
              return (
                <button key={c.id} className="li" onClick={() => { window.location.hash = `/app/report?id=${c.id}`; }}>
                  <Avatar name={NAMES[c.persona] || c.persona} hue={PERSONA_HUE[c.persona] ?? 330} size="sm" />
                  <div className="grow">
                    <div className="t">{NAMES[c.persona] || c.persona} · {mmss(c.wasted_seconds)}</div>
                    <div className="s">{new Date((c.started_at || 0) * 1000).toLocaleString("en-IN")} · {SCAM_TYPE_LABELS[type]}</div>
                  </div>
                  <Badge tone={n ? "green" : "muted"}>{n} IDs</Badge>
                  <ChevronRight size={16} className="muted flex-none" />
                </button>
              );
            })}
          </div>
        </Card>
      </div>
    </>
  );
}
