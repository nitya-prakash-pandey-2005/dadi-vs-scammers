// Scam ring radar: calls linked by a shared mule ID or by the scammer's voice fingerprint (Gnani clone embedding).
import { useEffect, useState } from "react";
import { AlertTriangle, AudioWaveform, Download, Network, RefreshCw } from "lucide-react";
import { Badge, Card, PageHead, Stat } from "../ui";
import { useApi } from "../lib/api";
import ApiLink from "../components/ApiLink";
import { SCAM_TYPE_LABELS } from "../lib/labels";

const W = 800, H = 440;
const short = (n) => (n.names?.[0] || n.id.slice(0, 6)).split(" ").slice(0, 2).join(" ");
const plain = (reason) => String(reason || "").replace(/\s*\([^)]*\)\s*$/, ""); // "same voice (1.00)" -> "same voice"

// pos[id] = [x, y, cx, cy]: node position plus its ring centre (labels and link text go on the outer side)
// first node angle: 2 calls stacked vertically, even rings turned half a step, so no node sits on the left/right
// edge where its name would collide with the neighbouring ring
const startAngle = (n) => (n === 2 ? -Math.PI / 2 : n % 2 === 0 ? -Math.PI / 2 + Math.PI / n : -Math.PI / 2);

// Wide cards: rings side by side, calls outside a ring in one row below.
// Narrow cards (phones): rings stacked, the other calls in rows of three, so nothing needs sideways scrolling.
const NW = 400, PER_ROW = 3;
function layout(data, narrow) {
  const pos = {};
  const rings = data.rings;
  const lone = data.nodes.filter((n) => !n.ring);
  const placeRing = (r, cx, cy) => {
    const n = r.calls.length, rad = n === 2 ? 105 : 95;
    r.calls.forEach((id, j) => {
      const a = (2 * Math.PI * j) / n + startAngle(n);
      pos[id] = [cx + rad * Math.cos(a), cy + rad * Math.sin(a), cx, cy];
    });
  };
  if (narrow) {
    rings.forEach((r, i) => placeRing(r, NW / 2, 155 + i * 300));
    const top = rings.length * 300 + (rings.length ? 20 : 40);
    lone.forEach((n, i) => {
      const row = Math.floor(i / PER_ROW), inRow = Math.min(PER_ROW, lone.length - row * PER_ROW);
      const x = (NW / (inRow + 1)) * ((i % PER_ROW) + 1), y = top + row * 80;
      pos[n.id] = [x, y, x, y - 140];
    });
    const rows = Math.ceil(lone.length / PER_ROW);
    return { pos, w: NW, h: rows ? top + (rows - 1) * 80 + 50 : rings.length * 300 + 10 };
  }
  rings.forEach((r, i) => placeRing(r, (W / (rings.length + 1)) * (i + 1), 170));
  const ly = rings.length ? H - 55 : 60; // row of calls that are not in a ring
  lone.forEach((n, i) => {
    const x = (W / (lone.length + 1)) * (i + 1);
    // many calls in one row: alternate labels above / below so names don't overlap
    const flip = lone.length > 5 && i % 2 === 1;
    pos[n.id] = [x, ly, x, flip ? ly + 140 : ly - 140];
  });
  return { pos, w: W, h: rings.length ? H : 130 }; // no rings yet: one short row of calls, not a big empty box
}

// true when the element is narrower than `px` (tracks resizes / rotation)
function useNarrow(px) {
  const [el, setEl] = useState(null); // callback ref: the element appears only once data has loaded
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.innerWidth < px);
  useEffect(() => {
    if (!el || typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(([e]) => setNarrow(e.contentRect.width < px));
    ro.observe(el);
    return () => ro.disconnect();
  }, [el, px]);
  return [setEl, narrow];
}

function Graph({ data, narrow }) {
  const { pos, w, h } = layout(data, narrow);
  const byId = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
  const ringOf = {};
  data.rings.forEach((r, i) => r.calls.forEach((id) => { ringOf[id] = i; }));
  // rings of 4+ calls: one caption in the middle instead of a label on every link (they would pile up)
  const big = (i) => i != null && data.rings[i].calls.length > 3;
  const open = (id) => { window.location.hash = `/app/report?id=${id}`; };
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={`ring-graph ${narrow ? "narrow" : ""}`} role="img" aria-label="Graph of linked scam calls">
      {data.links.map((l, i) => {
        if (!pos[l.source] || !pos[l.target]) return null;
        const [x1, y1, cx, cy] = pos[l.source], [x2, y2] = pos[l.target];
        const same = ringOf[l.source] === ringOf[l.target];
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, d = Math.hypot(mx - cx, my - cy) || 1;
        const off = same && d > 1 ? 16 : 0;
        const tx = mx + ((mx - cx) / d) * off, ty = (d > 1 ? my + ((my - cy) / d) * off : my - 8) + 4;
        return (
          <g key={i}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} className={`ring-link ${l.kind}`} />
            {!(same && big(ringOf[l.source])) && <text x={tx} y={ty} className="ring-reason">{l.reason}</text>}
          </g>
        );
      })}
      {data.rings.map((r, i) => {
        if (!big(i)) return null;
        const [, , cx, cy] = pos[r.calls[0]];
        const reasons = [...new Set(data.links.filter((l) => ringOf[l.source] === i && ringOf[l.target] === i).map((l) => plain(l.reason)))];
        return <text key={`c${i}`} x={cx} y={cy + 4} className="ring-reason ring-caption">{reasons.slice(0, 2).join(" · ")}</text>;
      })}
      {Object.entries(pos).map(([id, [x, y, , cy]]) => {
        const n = byId[id];
        if (!n) return null;
        const up = y < cy - 1, r = n.ring ? 16 : 10;
        const y1 = up ? y - r - 22 : y + r + 16, y2 = up ? y - r - 8 : y + r + 31;
        return (
          <g key={id} className={`ring-node ${n.ring ? "hot" : ""}`} role="link" tabIndex={0} aria-label={`Report for call ${id.slice(0, 6)} (${short(n)})`}
            onClick={() => open(id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(id); } }}>
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
  const [wrapRef, narrow] = useNarrow(560);
  const d = data || { nodes: [], links: [], rings: [] };
  const inRings = d.rings.reduce((a, r) => a + r.calls.length, 0);
  const synth = d.nodes.filter((n) => n.synthetic);
  return (
    <>
      <PageHead
        kicker="Intelligence"
        title="Scam ring radar"
        sub="One gang uses many names and many numbers. Dadi links calls that share a mule UPI ID, phone or account, or the same scammer's voice: Gnani's voice-cloning model turns ~10 s of their speech into a voice fingerprint. The same fingerprint flags callers who use a known AI voice."
        right={
          <div className="row wrap" style={{ gap: 8 }}>
            <ApiLink className="btn" href="/api/feed/mule-ids.csv" download><Download size={16} /> Mule-ID feed (CSV)</ApiLink>
            <button className="btn" onClick={reload} disabled={loading}><RefreshCw size={16} /> Refresh</button>
          </div>
        }
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
        {d.nodes.length ? <div className="ring-graph-wrap" ref={wrapRef}><Graph data={d} narrow={narrow} /></div> : <div className="empty">No calls yet. Run two arena calls with the same scammer voice and different scripts.</div>}
        {d.nodes.length > 0 && !d.rings.length && <div className="pill-src ring-hint">No links yet: calls join a ring when they share a mule ID or the same voice.</div>}
      </Card>
      <div className="grid g2" style={{ marginTop: 16 }}>
        {d.rings.map((r, i) => (
          <Card key={i} icon={AudioWaveform} title={`Ring ${i + 1}: ${r.calls.length} calls`} className="alert">
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
