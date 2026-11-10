import { useEffect, useRef } from "react";
import { AlertTriangle, AudioLines, CheckCircle2, FileText, Fingerprint, MessagesSquare, Network, Radar, Timer } from "lucide-react";
import { Badge, Card, Hud, Progress, Stat } from "../ui";
import SpeechText from "./SpeechText";
import { navigate } from "../lib/router";
import { INTEL_FIELDS, RED_FLAG_LABELS, SCAM_TYPE_LABELS, TACTIC_LABELS, mmss } from "../lib/labels";
import { useNow } from "../state/useCall";

export function TimeWasted({ call }) {
  const live = ["connecting", "live", "ending"].includes(call.phase);
  const now = useNow(live);
  const secs = live && call.startedAt ? ((call.frozenAt || now) - call.startedAt) / 1000 : call.phase === "ended" ? call.wasted : 0;
  return (
    <Card className="glow counter-card" icon={Timer} title="Scammer ka time barbaad" right={live ? <span className="pulse-dot" /> : null} tour="counter">
      <div className="big-counter grad-text">{mmss(secs)}</div>
      <div className="small text-2" style={{ marginTop: 8 }}>
        Every minute he spends with Dadi is a minute a real grandmother is safe.
      </div>
    </Card>
  );
}

export function ScamType({ intel }) {
  const type = intel?.scam_type || "other";
  const conf = intel?.scam_confidence || 0;
  return (
    <Card icon={Radar} title="Scam type">
      <Badge tone={type === "other" ? "muted" : "rose"} dot>{SCAM_TYPE_LABELS[type] || type}</Badge>
      <div className="row between" style={{ marginTop: 12 }}>
        <span className="small muted">Confidence</span>
        <span className="mono small">{Math.round(conf * 100)}%</span>
      </div>
      <Progress value={conf * 100} />
    </Card>
  );
}

export function Totals({ totals }) {
  const t = totals || { calls: 0, seconds_wasted: 0, mule_ids: 0 };
  return (
    <Card icon={Radar} title="All calls so far">
      <div className="grid g3 keep-3">
        <Stat value={t.calls} label="Scam calls answered" />
        <Stat value={mmss(t.seconds_wasted)} label="Scammer time wasted" tone="pink" />
        <Stat value={t.mule_ids} label="Mule IDs captured" tone="green" />
      </div>
    </Card>
  );
}

export function IntelCard({ intel }) {
  const validated = intel?.validated || {};
  const rows = INTEL_FIELDS.filter(([k]) => intel?.[k]?.length);
  const ok = (k, v) => (validated[k] || []).some((x) => String(x).toLowerCase() === String(v).toLowerCase());
  return (
    <Card icon={Fingerprint} title="Intel captured" right={<Hud tone="green">{rows.length ? "Live" : "Waiting"}</Hud>} tour="intel">
      {!rows.length && <div className="empty">Nothing yet. Dadi will get it out of him.</div>}
      <div className="intel-rows">
        {rows.map(([k, label]) => (
          <div key={k} className="intel-row">
            <Hud>{label}</Hud>
            <div className="chips">
              {intel[k].map((v) => (
                <span key={v} className={`idchip ${ok(k, v) ? "ok" : ""}`}>
                  {ok(k, v) && <CheckCircle2 size={13} />}
                  {v}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
      {rows.length > 0 && <div className="pill-src" style={{ marginTop: 10 }}>✓ = confirmed by pattern check (UPI / phone / account / IFSC format)</div>}
    </Card>
  );
}

export function RedFlags({ intel }) {
  const flags = [...(intel?.red_flags || [])].sort((a, b) => a.t - b.t);
  return (
    <Card icon={AlertTriangle} title="Red flags" right={<Badge tone={flags.length ? "rose" : "muted"}>{flags.length}</Badge>}>
      {!flags.length && <div className="empty">No red flags yet.</div>}
      <div className="list">
        {flags.map((f) => (
          <div className="li" key={f.flag}>
            <span className="mono small muted flag-time">{mmss(f.t)}</span>
            <div className="grow">
              <div className="t">{RED_FLAG_LABELS[f.flag] || f.flag}</div>
              {f.quote && <div className="flag-quote">“{f.quote}”</div>}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

const when = (s) => (s ? new Date(s * 1000).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : null);

// Dadi never forgets a voice: the caller's Gnani voice fingerprint matches an earlier call.
export function RepeatCaller({ match }) {
  if (!match) return null;
  const alias = match.names?.[0] || match.agencies?.[0];
  const type = match.scam_type ? SCAM_TYPE_LABELS[match.scam_type] || match.scam_type : null;
  const date = when(match.started_at);
  return (
    <Card className="alert" icon={AudioLines} title="Repeat scammer: Dadi knows this voice"
      right={<Badge tone="rose" dot>{Math.round((match.similarity || 0) * 100)}% voice match</Badge>}>
      <div className="small text-2">
        Same voice as {date ? <>the call on <b>{date}</b></> : "an earlier call"}
        {alias ? <>, when he called himself <b>{alias}</b></> : null}
        {type ? <> ({type})</> : null}. Dadi will tease him about it, in character.
      </div>
      {match.ids?.length > 0 && (
        <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>
          {match.ids.map((id) => <Badge key={id} tone="muted">{id}</Badge>)}
        </div>
      )}
      <div className="row wrap" style={{ gap: 8, marginTop: 12 }}>
        <button className="btn sm" onClick={() => navigate(`/app/report?id=${match.call_id}`)}><FileText size={14} /> Earlier call's report</button>
        <button className="btn sm" onClick={() => navigate("/app/rings")}><Network size={14} /> Scam ring radar</button>
      </div>
      <div className="disclaimer" style={{ marginTop: 10 }}>
        <AlertTriangle size={13} className="flex-none" /> A voice match is a lead for investigators, not proof.
      </div>
    </Card>
  );
}

export function Transcript({ call }) {
  const boxRef = useRef(null);
  useEffect(() => {
    const el = boxRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [call.turns.length]);
  const name = call.persona?.name || "Dadi";
  const firstKnown = call.turns.findIndex((t) => t.speaker !== "scammer" && t.recognised);
  return (
    <Card icon={MessagesSquare} title="Live transcript" right={call.speaking ? <Badge tone="pink" dot>{name} speaking</Badge> : null} tour="transcript">
      <div className="chat" ref={boxRef}>
        {!call.turns.length && <div className="empty">Press “Call Dadi” and play the scammer. Every line appears here as Prisma hears it.</div>}
        {call.turns.map((t, i) => {
          const scammer = t.speaker === "scammer";
          return (
            <div key={i} className={`bubble ${scammer ? "them" : "me"}`}>
              <div className="bubble-text"><SpeechText text={t.text} /></div>
              <div className="meta">
                {scammer ? "Scammer" : name} · {mmss(t.t)}
                {scammer && t.latency_ms != null ? ` · Prisma ${Math.round(t.latency_ms)} ms` : ""}
                {!scammer && t.tactic ? ` · ${TACTIC_LABELS[t.tactic] || t.tactic}` : ""}
                {!scammer && t.fallback ? " · fallback line" : ""}
                {i === firstKnown ? " · Recognised his voice" : ""}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export default function WarRoom({ call, totals }) {
  return (
    <div className="grid g-12 warroom">
      <div className="span-7"><TimeWasted call={call} /></div>
      <div className="span-5"><ScamType intel={call.intel} /></div>
      {call.repeat && <div className="span-12"><RepeatCaller match={call.repeat} /></div>}
      {call.phase === "ended" && call.callId && (
        <div className="span-12">
          <Card className="good">
            <div className="row between wrap">
              <div>
                <b>Call over. Dadi kept him busy for {mmss(call.wasted)}.</b>
                <div className="small text-2">Turn everything he revealed into a complaint draft for cybercrime.gov.in / 1930.</div>
              </div>
              <button className="btn primary" onClick={() => navigate(`/app/report?id=${call.callId}`)}>
                <FileText size={16} /> Generate complaint report
              </button>
            </div>
          </Card>
        </div>
      )}
      <div className="span-7"><Transcript call={call} /></div>
      <div className="span-5 stack">
        <IntelCard intel={call.intel} />
        <RedFlags intel={call.intel} />
      </div>
      <div className="span-12"><Totals totals={totals} /></div>
    </div>
  );
}
