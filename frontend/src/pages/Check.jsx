// Scam Message Checker: paste a suspicious SMS / WhatsApp / "notice", get a verdict and a Dadi reply to bait the sender.
import { useState } from "react";
import { AlertTriangle, CheckCircle2, Copy, MessageSquareWarning, Search, ShieldAlert, ShieldCheck } from "lucide-react";
import { Badge, Card, PageHead, toast } from "../ui";

const SAMPLES = [
  { label: "Digital arrest (Hinglish)", text: "CBI Mumbai: aapke Aadhaar se ek parcel mein drugs mile hain. Aap digital arrest mein hain, kisi ko mat batana. Jaanch ke liye turant 50,000 rupaye safe account rathore.cbi@okaxis par bhejo." },
  { label: "Bijli kat jayegi (Hindi)", text: "प्रिय उपभोक्ता, आपका बिजली कनेक्शन आज रात 9:30 बजे काट दिया जाएगा क्योंकि पिछला बिल अपडेट नहीं है। तुरंत बिजली अधिकारी से 98765 43210 पर संपर्क करें।" },
  { label: "KYC block (Tamil)", text: "உங்கள் SBI கணக்கு இன்று முடக்கப்படும். KYC update செய்ய இந்த link-ஐ click செய்யுங்கள்: sbi-kyc-update.top மற்றும் OTP-ஐ பகிருங்கள்." },
];
const VERDICT = {
  scam: { tone: "rose", icon: ShieldAlert, text: "Scam. Do not pay, do not reply with real details." },
  suspicious: { tone: "amber", icon: AlertTriangle, text: "Suspicious. Check with the real organisation first." },
  no_signs: { tone: "green", icon: ShieldCheck, text: "No scam signs found. Stay careful anyway." },
};
const ID_LABEL = { upi_ids: "UPI ID", phones: "Phone", accounts: "Account", ifsc: "IFSC", urls: "Link", apps: "App", amounts: "Amount" };

export default function Check() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [r, setR] = useState(null);

  const run = async () => {
    setBusy(true); setR(null);
    try {
      const res = await fetch("/api/check", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
      if (!res.ok) throw new Error(await res.text());
      setR(await res.json());
    } catch { toast("Could not check the message", "warn"); }
    setBusy(false);
  };
  const v = r && VERDICT[r.verdict];

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
              <button className="btn primary block" disabled={busy || !text.trim()} onClick={run}><Search size={16} /> {busy ? "Checking…" : "Check message"}</button>
            </div>
          </Card>
        </div>
        <div className="span-7 stack">
          {!r && <Card icon={ShieldCheck} title="Result"><div className="empty">Paste a message or pick a sample.</div></Card>}
          {r && (
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
                  {Object.keys(r.identifiers).length > 0 && (
                    <div><div className="pill-src">Details to report</div>
                      <div className="chips">{Object.entries(r.identifiers).flatMap(([k, vals]) => vals.map((x) => <Badge key={k + x} tone="rose">{ID_LABEL[k] || k}: {x}</Badge>))}</div>
                    </div>
                  )}
                  <div className="pill-src">Report at: {r.report_at.join(" · ")}</div>
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
