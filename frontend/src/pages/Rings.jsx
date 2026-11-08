// Scam ring radar: calls linked by a shared mule ID or by the scammer's voice fingerprint (Gnani clone embedding).
import { AlertTriangle, AudioWaveform, Network, RefreshCw } from "lucide-react";
import { Badge, Card, PageHead, Stat } from "../ui";
import { useApi } from "../lib/api";
import { SCAM_TYPE_LABELS } from "../lib/labels";

const W = 800, H = 320;
const short = (n) => (n.names?.[0] || n.id.slice(0, 6)).split(" ").slice(0, 2).join(" ");

function layout(data) {
  const pos = {};
  const rings = data.rings;
  rings.forEach((r, i) => {
    const cx = (W / (rings.length + 1)) * (i + 1), cy = 130, rad = r.calls.length === 2 ? 120 : 85;
    r.calls.forEach((id, j) => {
      const a = (2 * Math.PI * j) / r.calls.length + (r.calls.length === 2 ? Math.PI : -Math.PI / 2);
      pos[id] = [cx + rad * Math.cos(a), cy + rad * Math.sin(a)];
    });
  });
  const lone = data.nodes.filter((n) => !n.ring);
  lone.forEach((n, i) => { pos[n.id] = [(W / (lone.length + 1)) * (i + 1), H - 36]; });
  return pos;
}

function Graph({ data }) {
  const pos = layout(data);
  const byId = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="ring-graph" role="img" aria-label="Graph of linked scam calls">
      {data.links.map((l, i) => {
        const [x1, y1] = pos[l.source], [x2, y2] = pos[l.target];
        return (
          <g key={i}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} className={`ring-link ${l.kind}`} />
            <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 6} className="ring-reason">{l.reason}</text>
          </g>
        );
      })}
      {Object.entries(pos).map(([id, [x, y]]) => {
        const n = byId[id];
        return (
          <g key={id} className={`ring-node ${n.ring ? "hot" : ""}`} onClick={() => { window.location.hash = `/app/report?id=${id}`; }}>
            <circle cx={x} cy={y} r={n.ring ? 16 : 10} />
            <text x={x} y={y + (n.ring ? 32 : 24)}>{short(n)}</text>
          </g>
        );
      })}
    </svg>
  );
}

export default function Rings() {
  const { data, reload, loading } = useApi("/api/rings");
  const d = data || { nodes: [], links: [], rings: [] };
  const inRings = d.rings.reduce((a, r) => a + r.calls.length, 0);
  return (
    <>
      <PageHead
        kicker="Intelligence"
        title="Scam ring radar"
        sub="One gang uses many names and many numbers. Dadi links calls that share a mule UPI ID, phone or account, or the same scammer's voice: Gnani's voice-cloning model turns ~10 s of their speech into a voice fingerprint."
        right={<button className="btn" onClick={reload} disabled={loading}><RefreshCw size={16} /> Refresh</button>}
      />
      <div className="disclaimer" style={{ marginBottom: 16 }}>
        <AlertTriangle size={14} className="flex-none" /> Simulated calls with synthetic data. A voice match is a lead for investigators, not proof.
      </div>
      <div className="grid g4 keep-2" style={{ marginBottom: 16 }}>
        <Stat value={d.nodes.length} label="Scam calls" />
        <Stat value={d.rings.length} label="Rings found" tone={d.rings.length ? "rose" : undefined} />
        <Stat value={inRings} label="Calls linked to a ring" />
        <Stat value={d.nodes.filter((n) => n.voiceprint).length} label="Voice fingerprints" tone="cyan" />
      </div>
      <Card icon={Network} title="Who is behind the calls" right={<span className="ring-legend"><i className="id" /> same mule ID <i className="voice" /> same voice</span>}>
        {d.nodes.length ? <Graph data={d} /> : <div className="empty">No calls yet. Run two arena calls with the same scammer voice and different scripts.</div>}
      </Card>
      <div className="grid g2" style={{ marginTop: 16 }}>
        {d.rings.map((r, i) => (
          <Card key={i} icon={AudioWaveform} title={`Ring ${i + 1}: ${r.calls.length} calls`} className="bad">
            <div className="stack" style={{ gap: 10 }}>
              <div><div className="pill-src">Names used</div><div className="chips">{r.aliases.length ? r.aliases.map((a) => <Badge key={a} tone="amber">{a}</Badge>) : "–"}</div></div>
              <div><div className="pill-src">Mule IDs to freeze</div><div className="chips">{r.ids.length ? r.ids.map((x) => <Badge key={x} tone="rose">{x}</Badge>) : "–"}</div></div>
              <div><div className="pill-src">Scripts</div><div className="chips">{r.scam_types.map((s) => <Badge key={s}>{SCAM_TYPE_LABELS[s] || s}</Badge>)}</div></div>
              <div className="chips">{r.calls.map((c) => <a key={c} className="btn sm" href={`#/app/report?id=${c}`}>Report {c.slice(0, 6)}</a>)}</div>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
