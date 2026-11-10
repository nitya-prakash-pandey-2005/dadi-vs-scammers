// Scam intelligence board: who scammers pretend to be, what they ask for, and the mule IDs banks should freeze.
import { AlertTriangle, Building2, Download, Landmark, ShieldAlert, Snowflake } from "lucide-react";
import { Badge, Card, PageHead, Stat } from "../ui";
import { useApi } from "../lib/api";
import ApiLink from "../components/ApiLink";
import { RED_FLAG_LABELS, SCAM_TYPE_LABELS } from "../lib/labels";
import { lazy, Suspense } from "react";

const ScriptDonut = lazy(() => import("../components/viz/ScriptDonut"));

const inr = (n) => (n >= 1e7 ? `₹${(n / 1e7).toFixed(1)} Cr` : n >= 1e5 ? `₹${(n / 1e5).toFixed(1)} L` : `₹${n.toLocaleString("en-IN")}`);

function Bars({ rows, label, value, tone = "var(--rose)" }) {
  if (!rows?.length) return <div className="empty">Nothing yet.</div>;
  const max = Math.max(...rows.map(value));
  return (
    <div className="bars">
      {rows.map((r, i) => (
        <div key={i} className="bar-row">
          <span className="bar-label" title={label(r)}>{label(r)}</span>
          <span className="bar-track"><span className="bar-fill" style={{ width: `${(100 * value(r)) / max}%`, background: tone }} /></span>
          <span className="bar-n">{value(r)}</span>
        </div>
      ))}
    </div>
  );
}

export default function Intel() {
  const { data: i } = useApi("/api/insights");
  const { data: rows } = useApi("/api/freeze-list");
  const d = i || { calls: 0, minutes_wasted: 0, rupees_demanded: 0, agencies: [], scam_types: [], red_flags: [], handles: [] };
  return (
    <>
      <PageHead
        kicker="Intelligence"
        title="Scam intelligence board"
        sub="Every call Dadi takes becomes data: who the scammers pretend to be, how much they demand, and which mule accounts banks should freeze."
        right={<ApiLink className="btn primary" href="/api/freeze-list?format=csv"><Download size={16} /> Freeze list (CSV)</ApiLink>}
      />
      <div className="disclaimer" style={{ marginBottom: 16 }}>
        <AlertTriangle size={14} className="flex-none" /> Simulated calls with synthetic data. Bank names come from the UPI handle; confirm with NPCI before acting.
      </div>
      <div className="grid g4 keep-2" style={{ marginBottom: 16 }}>
        <Stat value={d.calls} label="Scam calls taken" />
        <Stat value={d.minutes_wasted} unit="min" label="Scammer time wasted" tone="green" />
        <Stat value={inr(d.rupees_demanded)} label="Money demanded (not paid)" tone="rose" />
        <Stat value={rows?.length ?? 0} label="Mule IDs captured" tone="cyan" />
      </div>
      <div className="grid g3">
        <Card icon={Building2} title="Who they pretend to be"><Bars rows={d.agencies} label={(r) => r.name} value={(r) => r.calls} /></Card>
        <Card icon={ShieldAlert} title="Scam scripts">
          {d.scam_types?.length ? (
            <Suspense fallback={<Bars rows={d.scam_types} label={(r) => SCAM_TYPE_LABELS[r.type] || r.type} value={(r) => r.calls} tone="var(--amber)" />}>
              <ScriptDonut rows={d.scam_types.map((r) => ({ name: SCAM_TYPE_LABELS[r.type] || r.type, value: r.calls }))} />
            </Suspense>
          ) : <div className="empty">Nothing yet.</div>}
        </Card>
        <Card icon={AlertTriangle} title="Pressure tactics"><Bars rows={d.red_flags} label={(r) => RED_FLAG_LABELS[r.flag] || r.flag} value={(r) => r.calls} tone="var(--cyan)" /></Card>
      </div>
      <Card icon={Snowflake} title="Freeze list: mule IDs to report" className="bad" style={{ marginTop: 16 }} right={<span className="pill-src">{d.handles.map((h) => `${h.handle} → ${h.bank || "?"}`).join(" · ")}</span>}>
        {!rows?.length ? <div className="empty">No mule IDs yet. Run an arena call.</div> : (
          <div className="table-wrap">
            <table className="freeze">
              <thead><tr><th>Type</th><th>ID</th><th>Alert</th><th>Ring</th><th>Calls</th><th>Names used</th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.kind + r.id}>
                    <td>{r.kind}</td><td className="mono">{r.id}</td>
                    <td>{r.bank ? <><Landmark size={13} /> {r.bank}</> : "–"}</td>
                    <td>{r.ring ? <Badge tone="rose">Ring {r.ring}</Badge> : "–"}</td>
                    <td>{r.calls.map((c) => <a key={c} href={`#/app/report?id=${c}`} className="mono">{c.slice(0, 6)} </a>)}</td>
                    <td>{r.names.join(", ") || "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
