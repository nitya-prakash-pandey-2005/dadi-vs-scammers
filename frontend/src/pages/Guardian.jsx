// Guardian: protects a REAL elder on her own call. She puts the call on speaker next to this page; Guardian listens
// (Gnani Prisma), scores the caller's words for scam red flags on every turn and, when the risk crosses a level,
// speaks one short calm warning to her in her language (Gnani Timbre). It never talks to the caller, stores nothing.
// Demo build: replays the caller's side of the real recorded call through the same rules, client side.
import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Info, Mic, MessageCircle, Phone, Play, ShieldAlert, ShieldCheck, Square, Volume2 } from "lucide-react";
import { createPcmPlayer, startMic } from "@voice/index.js";
import { Badge, Card, PageHead, toast } from "../ui";
import { DEMO, DEMO_CALL_AUDIO } from "../demo";
import RULES from "../lib/guardian-rules.json";
import { LEVELS, createTracker, warningText } from "../lib/guardian.js";

const RATE = 8000;
const LANGS = ["hi", "ta", "bn", "kn", "te", "en"];
const LEVEL_UI = {
  safe: { tone: "green", color: "var(--green)", icon: ShieldCheck, title: "No scam signs yet", sub: "Guardian is listening quietly." },
  caution: { tone: "amber", color: "var(--amber)", icon: AlertTriangle, title: "Be careful", sub: "This call shows signs of a scam. Share nothing." },
  stop: { tone: "rose", color: "var(--rose)", icon: ShieldAlert, title: "Stop: this looks like a scam", sub: "Hang up. Then tell your family and report it." },
};
const familyText = (reasons) => {
  const why = reasons.slice(0, 3).map((r) => r.text.replace(/^\+\d+: /, "")).join("; ");
  return `Guardian alert: I am on a suspicious phone call. The caller ${why}. Please call me now.`;
};

function Meter({ score, level }) {
  const ui = LEVEL_UI[level];
  const r = 80;
  const len = Math.PI * r;
  const th = RULES.thresholds;
  const tick = (v) => {
    const a = Math.PI * (1 - v / 100);
    return { x1: 100 + (r - 14) * Math.cos(a), y1: 100 - (r - 14) * Math.sin(a), x2: 100 + (r + 14) * Math.cos(a), y2: 100 - (r + 14) * Math.sin(a) };
  };
  return (
    <div className="guard-meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={score} aria-label={`Scam risk ${score} of 100: ${ui.title}`}>
      <svg viewBox="0 0 200 116" width="100%">
        <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="var(--line, rgba(255,255,255,0.1))" strokeWidth="16" strokeLinecap="round" />
        <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke={ui.color} strokeWidth="16" strokeLinecap="round"
          strokeDasharray={len} strokeDashoffset={len * (1 - score / 100)} style={{ transition: "stroke-dashoffset 0.8s ease, stroke 0.4s" }} />
        {[th.caution, th.stop].map((v) => <line key={v} {...tick(v)} stroke="var(--muted)" strokeWidth="1.5" opacity="0.6" />)}
        <text x="100" y="88" textAnchor="middle" className="guard-score" fill="currentColor">{score}</text>
        <text x="100" y="108" textAnchor="middle" className="guard-of" fill="var(--muted)">scam risk / 100</text>
      </svg>
      <div className="guard-level" style={{ color: ui.color }}><ui.icon size={22} /> {ui.title}</div>
      <div className="text-2 guard-sub">{ui.sub}</div>
    </div>
  );
}

// The caller's turns of the real recorded call (public/demo/ws-call.json), with their times
async function recordedCallerTurns() {
  const rows = await (await fetch("/demo/ws-call.json")).json();
  return rows.filter((r) => r.msg?.type === "turn" && r.msg.speaker === "scammer").map((r) => ({ t: r.t, text: r.msg.text }));
}

// Plays only the caller (left channel) of the stereo recording, in both ears
function callerAudio(rate) {
  const audio = new Audio(DEMO_CALL_AUDIO);
  audio.playbackRate = rate;
  let ctx = null;
  try {
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    const split = ctx.createChannelSplitter(2);
    ctx.createMediaElementSource(audio).connect(split);
    split.connect(ctx.destination, 0);
  } catch { ctx = null; }
  audio.play().catch(() => {});
  return { stop() { audio.pause(); ctx?.close().catch(() => {}); } };
}

export default function Guardian() {
  const [lang, setLang] = useState("hi");
  const [phase, setPhase] = useState("idle"); // idle | live | ended
  const [speed, setSpeed] = useState(1);
  const [risk, setRisk] = useState({ score: 0, level: "safe", reasons: [] });
  const [turns, setTurns] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const run = useRef(null);
  const listRef = useRef(null);

  const reset = () => { setRisk({ score: 0, level: "safe", reasons: [] }); setTurns([]); setWarnings([]); };
  const onEvent = (m) => {
    if (m.type === "turn" && m.speaker === "caller") setTurns((t) => [...t, m]);
    else if (m.type === "risk") setRisk({ score: m.score, level: m.level, reasons: m.reasons || [] });
    else if (m.type === "warning") { setWarnings((w) => [...w, m]); toast(m.level === "stop" ? "Guardian: stop, hang up" : "Guardian: be careful", m.level === "stop" ? "warn" : "info"); }
    else if (m.type === "guardian_language" && LANGS.includes(m.language)) setLang(m.language);
    else if (m.type === "call_ended") stop();
  };

  const stop = () => {
    const r = run.current;
    run.current = null;
    if (!r) return;
    r.timers?.forEach(clearTimeout);
    r.audio?.stop();
    r.mic?.stop();
    if (r.ws) { try { if (r.ws.readyState === WebSocket.OPEN) r.ws.send(JSON.stringify({ type: "hangup" })); r.ws.close(); } catch { /* closed */ } }
    r.player?.close?.();
    setPhase("ended");
  };
  useEffect(() => () => stop(), []); // leaving the page ends the session
  useEffect(() => { const el = listRef.current; if (el) el.scrollTop = el.scrollHeight; }, [turns.length]); // the list only, never the page

  // Demo: the caller's real words, through the same rules as the backend (guardian-rules.json), on the call's clock
  const playRecorded = async () => {
    stop(); reset();
    let lines;
    try { lines = await recordedCallerTurns(); } catch { toast("Could not load the recorded call", "warn"); return; }
    const r = { timers: [] };
    run.current = r;
    setPhase("live");
    if (speed === 1) r.audio = callerAudio(1);
    const tracker = createTracker(RULES);
    const warned = [];
    lines.forEach((line, i) => {
      r.timers.push(setTimeout(() => {
        if (run.current !== r) return;
        onEvent({ type: "turn", speaker: "caller", text: line.text, t: line.t });
        tracker.add(line.text);
        const level = tracker.level();
        onEvent({ type: "risk", score: tracker.score(), level, reasons: [...tracker.reasons] });
        if (level !== "safe" && !warned.includes(level)) {
          LEVELS.slice(1, LEVELS.indexOf(level) + 1).forEach((lv) => { if (!warned.includes(lv)) warned.push(lv); });
          onEvent({ type: "warning", level, text: warningText(RULES, lang, level), t: line.t });
        }
        if (i === lines.length - 1) r.timers.push(setTimeout(() => { if (run.current === r) stop(); }, 2500 / speed));
      }, (line.t * 1000) / speed));
    });
  };

  // Live: the elder's call on speaker -> mic -> /ws/guard; Guardian's warnings play through this device
  const startLive = async () => {
    stop(); reset();
    const r = { player: createPcmPlayer({ sampleRate: RATE }) };
    run.current = r;
    setPhase("live");
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/guard`);
    ws.binaryType = "arraybuffer";
    r.ws = ws;
    ws.onopen = () => ws.send(JSON.stringify({ type: "start", language: lang }));
    ws.onmessage = (e) => {
      if (run.current !== r) return;
      if (typeof e.data === "string") { try { onEvent(JSON.parse(e.data)); } catch { /* ignore */ } }
      else r.player.play(e.data);
    };
    ws.onerror = () => toast("Could not reach the Guardian server", "warn");
    ws.onclose = () => { if (run.current === r) stop(); };
    try {
      r.mic = await startMic({ targetRate: RATE, onFrame: (ab) => { if (run.current === r && ws.readyState === WebSocket.OPEN && ws.bufferedAmount < 256 * 1024) ws.send(ab); } });
      if (run.current !== r) r.mic.stop();
    } catch {
      toast("Microphone permission is needed to listen to the call", "warn");
      stop();
    }
  };

  const ui = LEVEL_UI[risk.level];
  const msg = familyText(risk.reasons);
  const alertOn = risk.level === "stop";
  return (
    <>
      <PageHead kicker="Protects real elders" title="Guardian"
        sub="Dadi wastes scammers' time. Guardian protects the person they actually call: put the suspicious call on speaker next to this page. It listens, scores every sentence for scam red flags, and calmly warns her, in her language, when the risk gets high. It never speaks to the caller and saves nothing." />
      {DEMO && (
        <div className="disclaimer" style={{ marginBottom: 16 }}>
          <Info size={14} className="flex-none" /> Demo: replays the caller's side of a real call recorded on Gnani's live servers (synthetic caller) through the same scoring rules. In the live app Guardian speaks these warnings aloud with Gnani Timbre.
        </div>
      )}
      <div className="grid g-12">
        <div className="span-5 stack">
          <Card icon={ui.icon} title="Scam risk" right={<Badge tone={ui.tone} dot>{risk.level}</Badge>}>
            <Meter score={risk.score} level={risk.level} />
          </Card>
          <Card icon={Volume2} title="Her language">
            <div className="stack" style={{ gap: 12 }}>
              <div className="chips" role="group" aria-label="Warning language">
                {LANGS.map((k) => (
                  <button key={k} className={`btn sm ${lang === k ? "primary" : ""}`} aria-pressed={lang === k} disabled={phase === "live"} onClick={() => setLang(k)}>{RULES.languages[k].name}</button>
                ))}
              </div>
              {DEMO ? (
                <>
                  <div className="chips" role="group" aria-label="Replay speed">
                    {[1, 4].map((s) => <button key={s} className={`btn sm ${speed === s ? "primary" : ""}`} aria-pressed={speed === s} disabled={phase === "live"} onClick={() => setSpeed(s)}>{s === 1 ? "Real time, with the caller's voice" : "4× fast, silent"}</button>)}
                  </div>
                  {phase === "live"
                    ? <button className="btn danger block" onClick={stop}><Square size={16} /> Stop the replay</button>
                    : <button className="btn primary block" onClick={playRecorded}><Play size={16} /> Play a recorded call</button>}
                </>
              ) : phase === "live"
                ? <button className="btn danger block" onClick={stop}><Square size={16} /> Stop listening</button>
                : <button className="btn primary block" onClick={startLive}><Mic size={16} /> Start Guardian (call on speaker)</button>}
            </div>
          </Card>
          <Card icon={Phone} title="Get help" right={alertOn ? <Badge tone="rose" dot>now</Badge> : null}>
            <div className="stack" style={{ gap: 10 }}>
              <p className="text-2">{alertOn ? "Hang up first. Then tell your family and report the call." : "Shows up in red when the risk reaches stop. You can always report a call."}</p>
              <div className="guard-actions">
                <a className={`btn ${alertOn ? "primary" : ""}`} aria-disabled={!alertOn} tabIndex={alertOn ? 0 : -1} onClick={(e) => { if (!alertOn) e.preventDefault(); }}
                  href={`https://wa.me/?text=${encodeURIComponent(msg)}`} target="_blank" rel="noreferrer"><MessageCircle size={16} /> Alert my family (WhatsApp)</a>
                <a className="btn" aria-disabled={!alertOn} tabIndex={alertOn ? 0 : -1} onClick={(e) => { if (!alertOn) e.preventDefault(); }}
                  href={`sms:?&body=${encodeURIComponent(msg)}`}><MessageCircle size={16} /> Alert by SMS</a>
                <a className="btn" href="tel:1930"><Phone size={16} /> Report on 1930</a>
                <a className="btn" href="https://cybercrime.gov.in" target="_blank" rel="noreferrer"><ShieldAlert size={16} /> cybercrime.gov.in</a>
              </div>
            </div>
          </Card>
        </div>
        <div className="span-7 stack">
          <Card icon={Volume2} title="Warnings Guardian spoke to her">
            {warnings.length === 0
              ? <div className="empty">Silent so far. Guardian speaks only when the risk crosses {RULES.thresholds.caution} (be careful) or {RULES.thresholds.stop} (stop), once each.</div>
              : <ul className="guard-list">{warnings.map((w, i) => (
                  <li key={i} className={`guard-warning lv-${w.level}`}><Badge tone={LEVEL_UI[w.level].tone}>{w.level === "stop" ? "stop" : "be careful"}</Badge><span lang={lang}>{w.text}</span></li>
                ))}</ul>}
          </Card>
          <Card icon={AlertTriangle} title="Why the risk went up">
            {risk.reasons.length === 0
              ? <div className="empty">No red flags yet.</div>
              : <ul className="guard-list">{risk.reasons.map((r) => (
                  <li key={r.flag} className="guard-reason"><b style={{ color: "var(--rose)" }}>+{r.points}</b><span>{r.text.replace(/^\+\d+: /, "")}<span className="text-2"> · heard “{r.heard}”</span></span></li>
                ))}</ul>}
          </Card>
          <Card icon={Mic} title="What the caller said" right={phase === "live" ? <Badge tone="cyan" dot>listening</Badge> : null}>
            {turns.length === 0
              ? <div className="empty">{DEMO ? "Press “Play a recorded call”." : "Start Guardian and put the call on speaker."}</div>
              : <ul ref={listRef} className="guard-list guard-transcript">{turns.map((t, i) => <li key={i}><span className="text-2 mono guard-t">{Number(t.t || 0).toFixed(0)}s</span><span>{t.text}</span></li>)}</ul>}
          </Card>
        </div>
      </div>
    </>
  );
}
