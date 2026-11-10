// Scam Message Checker: paste a suspicious SMS / WhatsApp / "notice", get a verdict and a Dadi reply to bait the sender.
import CheckGuide from "../components/viz/CheckGuide";
import { useState } from "react";
import { AlertTriangle, CheckCircle2, Copy, Info, MessageSquareWarning, Network, Search, Share2, ShieldAlert, ShieldCheck } from "lucide-react";
import { Badge, Card, PageHead, toast } from "../ui";
import { postJSON } from "../lib/api";
import { SAMPLES } from "../lib/checkSamples";
import { HAS_CHECKS, REPO_URL } from "../demo";

const VERDICT = {
  scam: { tone: "rose", icon: ShieldAlert, text: "Scam. Do not pay, do not reply with real details." },
  suspicious: { tone: "amber", icon: AlertTriangle, text: "Suspicious. Check with the real organisation first." },
  no_signs: { tone: "green", icon: ShieldCheck, text: "No scam signs found. Stay careful anyway." },
};
const shareText = (r, v) => `${v.text}\n${r.fact}\nReport: sancharsaathi.gov.in (Chakshu) or call 1930.\nChecked with Dadi vs Scammers`;
const ID_LABEL = { upi_ids: "UPI ID", phones: "Phone", accounts: "Account", ifsc: "IFSC", urls: "Link", apps: "App", amounts: "Amount" };

export default function Check() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [r, setR] = useState(null);

  const run = async (msg = text) => {
    setBusy(true); setR(null);
    try {
      setR(await postJSON("/api/check", { text: msg }));
    } catch { toast("Could not check the message", "warn"); }
    setBusy(false);
  };
  const v = r && VERDICT[r.verdict];
  const note = r?.demo_note; // demo build: free text has no recorded verdict

  return (
    <>
      <PageHead kicker="For everyone" title="Check a suspicious message"
        sub="Paste an SMS, WhatsApp message or 'notice' in any Indian language or Hinglish. Dadi tells you if it's a scam, what the true fact is, and writes a reply that wastes the scammer's time." />
      <div className="disclaimer" style={{ marginBottom: 16 }}>
        <AlertTriangle size={14} className="flex-none" /> Demo with synthetic messages. Do not paste real personal data. A verdict is advice, not a guarantee.
      </div>
      <div className="grid g-12">
        <div className="span-5 stack">
          <Card icon={MessageSquareWarning} title="The message">
            <div className="stack" style={{ gap: 10 }}>
              <textarea className="textarea" rows={7} value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the message here…" maxLength={2000} />
              <div className="chips">{SAMPLES.map((s) => <button key={s.label} className="btn sm" onClick={() => setText(s.text)}>{s.label}</button>)}</div>
              <button className="btn primary block" disabled={busy || !text.trim()} onClick={() => run()}><Search size={16} /> {busy ? "Checking…" : "Check message"}</button>
            </div>
          </Card>
        </div>
        <div className="span-7 stack">
          {!r && <Card icon={ShieldCheck} title="Result"><div className="empty">Paste a message or pick a sample.</div></Card>}
          {!r && <CheckGuide />}
          {note && (
            <Card icon={Info} title={HAS_CHECKS ? "Try a sample message in this demo" : "Checking needs the live server"}>
              <div className="stack" style={{ gap: 10 }}>
                <p className="text-2">
                  {HAS_CHECKS
                    ? "This online demo replays verdicts recorded from the live backend, so it can check the sample messages. Pick one of them. To check any message, run Dadi locally with your own keys."
                    : "The checker reads each message with a live LLM, which this online demo never calls. Run Dadi locally with your own keys to check any message."}
                </p>
                {HAS_CHECKS && <div className="chips">{SAMPLES.map((s) => <button key={s.label} className="btn sm" onClick={() => { setText(s.text); run(s.text); }}>{s.label}</button>)}</div>}
                <a className="btn sm" href={REPO_URL} target="_blank" rel="noreferrer">How to run it locally (GitHub)</a>
              </div>
            </Card>
          )}
          {r && !note && (
            <>
              <Card icon={v.icon} title={v.text} className={r.verdict === "scam" ? "bad" : r.verdict === "no_signs" ? "good" : ""}
                right={<Badge tone={v.tone}>{r.scam_type_label}</Badge>}>
                <div className="stack" style={{ gap: 10 }}>
                  <div className="fact"><CheckCircle2 size={16} className="flex-none" /> {r.fact}</div>
                  {r.claimed.length > 0 && <div><div className="pill-src">Pretends to be</div><div className="chips">{r.claimed.map((c) => <Badge key={c} tone="amber">{c}</Badge>)}</div></div>}
                  {r.red_flags.length > 0 && (
                    <div><div className="pill-src">Red flags</div>
                      <ul className="flags">{r.red_flags.map((f) => <li key={f.flag}><b>{f.label}</b>{f.quote ? `: “${f.quote}”` : ""}</li>)}</ul>
                    </div>
                  )}
                  {r.seen_before?.length > 0 && (
                    <div className="fact"><Network size={16} className="flex-none" />
                      <span>Dadi has heard this before: {r.seen_before.map((x) => (
                        <span key={x.id}><b>{x.id}</b> came up in {x.calls.length} scam call{x.calls.length > 1 ? "s" : ""} ({x.calls.map((c) => <a key={c} href={`#/app/report?id=${c}`}>{c.slice(0, 6)}</a>).reduce((a, b) => [a, ", ", b])}). </span>
                      ))}<a href="#/app/rings">See the ring</a></span>
                    </div>
                  )}
                  {r.risky_links?.length > 0 && (
                    <div><div className="pill-src">Dangerous links</div>
                      <ul className="flags">{r.risky_links.map((l) => <li key={l.url}><b>{l.url}</b>: {l.reasons.join("; ")}</li>)}</ul>
                    </div>
                  )}
                  {Object.keys(r.identifiers).length > 0 && (
                    <div><div className="pill-src">Details to report</div>
                      <div className="chips">{Object.entries(r.identifiers).flatMap(([k, vals]) => vals.map((x) => <Badge key={k + x} tone="rose">{ID_LABEL[k] || k}: {x}</Badge>))}</div>
                    </div>
                  )}
                  <div className="pill-src">Report at: {r.report_at.join(" · ")}</div>
                  <a className="btn sm" target="_blank" rel="noreferrer" href={`https://wa.me/?text=${encodeURIComponent(shareText(r, v))}`}>
                    <Share2 size={14} /> Warn the family on WhatsApp
                  </a>
                </div>
              </Card>
              {r.dadi_reply && (
                <Card icon={MessageSquareWarning} title="Reply as Dadi (wastes their time, gives nothing real)"
                  right={<button className="btn sm" onClick={() => { navigator.clipboard?.writeText(r.dadi_reply); toast("Copied", "info"); }}><Copy size={14} /> Copy</button>}>
                  <div className="bubble me"><div className="bubble-text">{r.dadi_reply}</div></div>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
