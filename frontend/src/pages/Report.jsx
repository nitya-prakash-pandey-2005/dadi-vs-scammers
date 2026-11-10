import { ArrowLeft, AudioLines, Download, Printer, ShieldAlert } from "lucide-react";
import { Badge, Card, Hud, PageHead } from "../ui";
import { useApi } from "../lib/api";
import { INTEL_FIELDS, mmss } from "../lib/labels";
import SpeechText from "../components/SpeechText";
import ApiLink from "../components/ApiLink";
import RecPlayer from "../components/viz/RecPlayer";
import { NOT_IN_DEMO, apiHref } from "../demo";

const REPORT_LINKS = {
  "cybercrime.gov.in": "https://cybercrime.gov.in",
  "Helpline 1930": "tel:1930",
};
const linkFor = (w) => REPORT_LINKS[w] || (w.includes("sancharsaathi") ? "https://sancharsaathi.gov.in" : null);
const FIELD_LABEL = Object.fromEntries(INTEL_FIELDS);

export default function Report({ query }) {
  const id = query?.id;
  const { data: r, error, loading } = useApi(id ? `/api/calls/${id}/report` : null);

  if (!id) return <div className="empty">No call selected. Open a report from “Calls & reports”.</div>;
  if (loading && !r) return <div className="skeleton" style={{ height: 320 }} />;
  if (error || !r) return <div className="empty">Could not load this report ({String(error?.message || "not found")}).</div>;

  const when = r.incident_time ? new Date(r.incident_time).toLocaleString("en-IN") : "-";
  const ids = Object.entries(r.suspect_identifiers || {});
  const recUrl = r.recording ? apiHref(r.recording.url) : null; // demo: the static copy, if the snapshot has it
  return (
    <div className="report">
      <PageHead
        kicker="Complaint draft"
        title={r.title}
        sub={`Call ${r.call_id} · ${r.persona} answered`}
        right={
          <div className="row no-print">
            <a className="btn ghost sm" href="#/app/history"><ArrowLeft size={15} /> Calls</a>
            <ApiLink className="btn sm" href={`/api/calls/${id}/evidence.zip`} download><Download size={15} /> Evidence pack</ApiLink>
            <button className="btn primary sm" onClick={() => window.print()}><Printer size={15} /> Print / save PDF</button>
          </div>
        }
      />

      <div className="grid">
        <Card className="warn">
          <div className="row-top"><ShieldAlert size={18} className="flex-none" /><span className="small">{r.disclaimer}</span></div>
        </Card>

        <Card title="Summary"><p className="text-2">{r.summary}</p></Card>

        {r.recording && (
          <Card icon={AudioLines} title="Call recording (evidence)" right={<Hud tone="green">SHA-256 sealed</Hud>}>
            {recUrl ? <RecPlayer src={recUrl} persona={r.persona} /> : <div className="empty no-print">{NOT_IN_DEMO}.</div>}
            <div className="small text-2" style={{ marginTop: 8 }}>
              Stereo: left = caller, right = {r.persona}, as it was heard on the call · {mmss(r.recording.seconds)}
            </div>
            <div className="hash mono">{r.recording.sha256}</div>
            <div className="small muted">
              The evidence pack holds the recording, the full transcript and this report, each with its SHA-256, so
              anyone can check that nothing was changed.
            </div>
          </Card>
        )}

        <div className="grid g2">
          <Card title="Incident">
            <dl className="facts">
              <dt>Time</dt><dd>{when}</dd>
              <dt>Duration</dt><dd className="mono">{mmss(r.duration_seconds)}</dd>
              <dt>Scam type</dt><dd><Badge tone="rose" dot>{r.scam_type_label}</Badge> <span className="mono small muted">{Math.round((r.scam_confidence || 0) * 100)}%</span></dd>
              <dt>Answered by</dt><dd>{r.persona} (AI decoy)</dd>
            </dl>
          </Card>
          <Card title="Claimed identity">
            <dl className="facts">
              <dt>Names</dt><dd>{r.claimed_identity?.names?.join(", ") || "-"}</dd>
              <dt>Agency</dt><dd>{r.claimed_identity?.agencies?.join(", ") || "-"}</dd>
              <dt>Amounts</dt><dd>{r.amounts_demanded?.join(", ") || "-"}</dd>
            </dl>
          </Card>
        </div>

        <Card title="Suspect identifiers">
          {!ids.length && <div className="empty">No identifiers were revealed on this call.</div>}
          <div className="intel-rows">
            {ids.map(([k, vals]) => (
              <div className="intel-row" key={k}>
                <Hud>{FIELD_LABEL[k] || k}</Hud>
                <div className="chips">{vals.map((v) => <span className="idchip" key={v}>{v}</span>)}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Red flags">
          {!r.red_flags?.length && <div className="empty">None recorded.</div>}
          <div className="list">
            {r.red_flags?.map((f) => (
              <div className="li" key={f.flag}>
                <span className="mono small muted flag-time">{mmss(f.t)}</span>
                <div className="grow">
                  <div className="t">{f.label}</div>
                  {f.quote && <div className="flag-quote">“{f.quote}”</div>}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Transcript excerpt">
          <div className="chat static">
            {r.transcript_excerpt?.map((t, i) => (
              <div key={i} className={`bubble ${t.speaker === "scammer" ? "them" : "me"}`}>
                <div className="bubble-text"><SpeechText text={t.text} /></div>
                <div className="meta">{t.speaker === "scammer" ? "Scammer" : r.persona} · {mmss(t.t)}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Where to report">
          <div className="list">
            {r.where_to_report?.map((w) => (
              <div className="li" key={w}>
                {linkFor(w) ? <a className="t" href={linkFor(w)} target="_blank" rel="noreferrer">{w}</a> : <span className="t">{w}</span>}
              </div>
            ))}
          </div>
          <div className="small muted" style={{ marginTop: 8 }}>File within the first hours: early reports on 1930 give banks the best chance to freeze money.</div>
        </Card>
      </div>
    </div>
  );
}
