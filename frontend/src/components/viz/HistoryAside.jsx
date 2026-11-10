// Right-hand context column for "Calls & reports" on wide screens: time wasted per call (Recharts, lazy chunk),
// the scam-type mix, what an evidence pack holds, and the honest demo note. Only real call data, nothing invented.
import { lazy, Suspense } from "react";
import { BarChart3, FileLock2, PieChart } from "lucide-react";
import { Card } from "../../ui";
import { SCAM_TYPE_LABELS } from "../../lib/labels";
import { DEMO, RECORDED_ON } from "../../demo";

const CallsChart = lazy(() => import("./CallsChart"));

export default function HistoryAside({ calls }) {
  const list = (calls || []).slice().sort((a, b) => (a.started_at || 0) - (b.started_at || 0));
  const types = {};
  list.forEach((c) => { const t = c.intel?.scam_type || "other"; types[t] = (types[t] || 0) + 1; });
  const mix = Object.entries(types).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...mix.map(([, n]) => n));
  return (
    <aside className="side-col">
      <Card icon={BarChart3} title="Scammer time wasted, per call">
        {list.length ? (
          <Suspense fallback={<div className="skeleton" style={{ height: 180 }} />}><CallsChart calls={list} /></Suspense>
        ) : <div className="empty">No calls yet.</div>}
      </Card>
      {!!mix.length && (
        <Card icon={PieChart} title="Scam types">
          <div className="mix">
            {mix.map(([t, n]) => (
              <div className="mix-row" key={t}>
                <span className="mix-l">{SCAM_TYPE_LABELS[t] || t}</span>
                <span className="mix-bar"><i style={{ transform: `scaleX(${n / max})` }} /></span>
                <span className="mix-n mono">{n}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
      <Card icon={FileLock2} title="What each evidence pack holds">
        <ul className="side-list">
          <li>Two-track recording: left = caller, right = Dadi as actually heard</li>
          <li>Full transcript and the complaint draft</li>
          <li>A manifest with each file's SHA-256, so anyone can check nothing changed</li>
        </ul>
        {DEMO && <div className="small muted" style={{ marginTop: 10 }}>Demo: calls recorded on Gnani's live servers on {RECORDED_ON}. Synthetic scammers, fake IDs.</div>}
      </Card>
    </aside>
  );
}
