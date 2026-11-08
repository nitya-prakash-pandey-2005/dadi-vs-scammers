// Scam ring radar: calls linked by a shared mule ID or by the scammer's voice fingerprint (Gnani clone embedding).
import { AlertTriangle, AudioWaveform, Network, RefreshCw } from "lucide-react";
import { Badge, Card, PageHead, Stat } from "../ui";
import { useApi } from "../lib/api";
import { SCAM_TYPE_LABELS } from "../lib/labels";

const W = 800, H = 420;
const short = (n) => (n.names?.[0] || n.id.slice(0, 6)).split(" ").slice(0, 2).join(" ");

// pos[id] = [x, y, cx, cy]: node position plus its ring centre (labels and link text go on the outer side)
function layout(data) {
  const pos = {};
  const rings = data.rings;
  rings.forEach((r, i) => {
    const cx = (W / (rings.length + 1)) * (i + 1), cy = 165, rad = r.calls.length === 2 ? 110 : 95;
    r.calls.forEach((id, j) => {
      const a = (2 * Math.PI * j) / r.calls.length + (r.calls.length === 2 ? Math.PI : -Math.PI / 2);
      pos[id] = [cx + rad * Math.cos(a), cy + rad * Math.sin(a), cx, cy];
    });
  });
  const lone = data.nodes.filter((n) => !n.ring);
  lone.forEach((n, i) => { const x = (W / (lone.length + 1)) * (i + 1); pos[n.id] = [x, H - 60, x, H - 200]; });
  return pos;
}

function Graph({ data }) {
  const pos = layout(data);
  const byId = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="ring-graph" role="img" aria-label="Graph of linked scam calls">
      {data.links.map((l, i) => {
        const [x1, y1, cx, cy] = pos[l.source], [x2, y2] = pos[l.target];
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, d = Math.hypot(mx - cx, my - cy) || 1;
        const off = l.source && pos[l.source][2] === pos[l.target][2] && d > 1 ? 16 : 0;
        const tx = mx + ((mx - cx) / d) * off, ty = (d > 1 ? my + ((my - cy) / d) * off : my - 8) + 4;
        return (
          <g key={i}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} className={`ring-link ${l.kind}`} />
            <text x={tx} y={ty} className="ring-reason">{l.reason}</text>
          </g>
        );
      })}
      {Object.entries(pos).map(([id, [x, y, , cy]]) => {
        const n = byId[id];
        const up = y < cy - 1, r = n.ring ? 16 : 10;
        const y1 = up ? y - r - 22 : y + r + 16, y2 = up ? y - r - 8 : y + r + 31;
        return (
          <g key={id} className={`ring-node ${n.ring ? "hot" : ""}`} onClick={() => { window.location.hash = `/app/report?id=${id}`; }}>
            <circle cx={x} cy={y} r={r} />
            <text x={x} y={y1}>{short(n)}</text>
            {n.synthetic && <text x={x} y={y2} className="ring-synth">AI voice? ({n.synthetic.voice})</text>}
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
  const synth = d.nodes.filter((n) => n.synthetic);
  return (
    <>
      <PageHead
        kicker="Intelligence"
        title="Scam ring radar"
        sub="One gang uses many names and many numbers. Dadi links calls that share a mule UPI ID, phone or account, or the same scammer's voice: Gnani's voice-cloning model turns ~10 s of their speech into a voice fingerprint. The same fingerprint flags callers who use a known AI voice."
        right={<button className="btn" onClick={reload} disabled={loading}><RefreshCw size={16} /> Refresh</button>}
      />
      <div className="disclaimer" style={{ marginBottom: 16 }}>
        <AlertTriangle size={14} className="flex-none" /> Simulated calls with synthetic data. A voice match is a lead for investigators, not proof.
      </div>
      <div className="grid g4 keep-2" style={{ marginBottom: 16 }}>
        <Stat value={d.nodes.length} label="Scam calls" />
        <Stat value={d.rings.length} label="Rings found" tone={d.rings.length ? "rose" : undefined} />
        <Stat value={inRings} label="Calls linked to a ring" />
        <Stat value={`${synth.length}/${d.nodes.filter((n) => n.voiceprint).length}`} label="Voices matching a known AI voice" tone="cyan" />
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
