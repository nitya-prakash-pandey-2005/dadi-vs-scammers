// Arena: AI scammer vs AI Dadi over a simulated noisy 8 kHz phone line, plus the Prisma noise benchmark.
import { useEffect, useRef, useState } from "react";
import { Activity, AlertTriangle, Bot, Gauge as GaugeIcon, Network, Play, Swords } from "lucide-react";
import { Badge, Card, Hud, PageHead, Progress, Seg, Stat, toast } from "../ui";
import { IntelCard, RepeatCaller } from "../components/WarRoom";
import SpeechText from "../components/SpeechText";
import { SCAM_TYPE_LABELS, TACTIC_LABELS, mmss } from "../lib/labels";

const SCAMS = [
  { value: "digital_arrest", label: "Digital arrest" },
  { value: "kyc_bank_block", label: "KYC block" },
  { value: "electricity_bill", label: "Electricity" },
  { value: "lottery_prize", label: "Lottery" },
];
const NOISE = [
  { value: "off", label: "Clean" },
  { value: "20", label: "20 dB" },
  { value: "10", label: "10 dB" },
  { value: "5", label: "5 dB" },
  { value: "0", label: "0 dB" },
];
const VOICES = [
  { value: "Harshad", label: "Harshad" },
  { value: "Avinash", label: "Avinash" },
  { value: "Yashraj", label: "Yashraj" },
];
const TURNS = [{ value: 4, label: "4 turns" }, { value: 6, label: "6 turns" }, { value: 8, label: "8 turns" }];
const pctTxt = (v) => (v == null ? "–" : `${Math.round(v * 100)}%`);
const snrLabel = (s) => (s == null ? "Clean" : `${s} dB`);

function openArena(payload, onEvent, onDone) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${window.location.host}/ws/arena`);
  ws.onopen = () => ws.send(JSON.stringify(payload));
  ws.onmessage = (e) => { try { onEvent(JSON.parse(e.data)); } catch { /* ignore */ } };
  ws.onerror = () => onEvent({ type: "error", message: "Could not reach the Dadi server" });
  ws.onclose = () => onDone();
  return ws;
}

export default function Arena() {
  const [scam, setScam] = useState("digital_arrest");
  const [noise, setNoise] = useState("10");
  const [turns, setTurns] = useState(6);
  const [voice, setVoice] = useState("Harshad");
  const [running, setRunning] = useState(null); // "arena" | "bench" | null
  const [feed, setFeed] = useState([]);
  const [intel, setIntel] = useState(null);
  const [summary, setSummary] = useState(null);
  const [repeat, setRepeat] = useState(null);
  const [bench, setBench] = useState({ rows: [], bySnr: null });
  const wsRef = useRef(null);
  const feedRef = useRef(null);

  useEffect(() => () => wsRef.current?.close(), []);
  useEffect(() => { feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" }); }, [feed]);

  const onEvent = (m) => {
    if (m.type === "arena_turn") setFeed((f) => [...f, m]);
    else if (m.type === "intel") setIntel(m.intel);
    else if (m.type === "arena_done") setSummary(m.summary);
    else if (m.type === "repeat_caller") setRepeat(m.match);
    else if (m.type === "bench_row") setBench((b) => ({ ...b, rows: [...b.rows, m] }));
    else if (m.type === "bench_done") setBench((b) => ({ ...b, bySnr: m.by_snr }));
    else if (m.type === "error") toast(m.message || "Arena error", "warn");
  };

  const runArena = () => {
    setFeed([]); setIntel(null); setSummary(null); setRepeat(null); setRunning("arena");
    wsRef.current = openArena(
      { type: "arena", scam_type: scam, turns, snr_db: noise === "off" ? null : Number(noise), persona: "dadi", scammer_voice: voice },
      onEvent, () => setRunning(null));
  };
  const runBench = () => {
    setBench({ rows: [], bySnr: null }); setRunning("bench");
    wsRef.current = openArena({ type: "benchmark", snr_list: [null, 20, 10, 5, 0] }, onEvent, () => setRunning(null));
  };
  const stop = () => { wsRef.current?.close(); setRunning(null); };
  const firstKnown = feed.findIndex((m) => m.speaker === "dadi" && m.recognised);

  return (
    <>
      <PageHead
        kicker="Arena"
        title="AI scammer vs AI Dadi"
        sub="Both sides are generated. The scammer is spoken by Gnani Timbre, squeezed into an 8 kHz phone line with call-centre noise, and heard by Gnani Prisma, so every turn really goes through audio."
        right={running ? <button className="btn danger" onClick={stop}>Stop</button> : null}
      />
      <div className="disclaimer" style={{ marginBottom: 16 }}>
        <AlertTriangle size={14} className="flex-none" /> Synthetic AI-vs-AI call. All names, UPI IDs and numbers are fake.
      </div>

      <div className="grid g-12">
        <div className="span-5 stack">
          <Card icon={Swords} title="Run a simulated scam call">
            <div className="stack" style={{ gap: 12 }}>
              <label className="field">Scam script<Seg options={SCAMS} value={scam} onChange={setScam} /></label>
              <label className="field">Call-centre noise (SNR)<Seg options={NOISE} value={noise} onChange={setNoise} /></label>
              <label className="field">Scammer's voice (Timbre)<Seg options={VOICES} value={voice} onChange={setVoice} /></label>
              <label className="field">Length<Seg options={TURNS} value={turns} onChange={setTurns} /></label>
              <button className="btn primary block" disabled={!!running} onClick={runArena}>
                <Play size={16} /> {running === "arena" ? "Call in progress…" : "Start AI-vs-AI call"}
              </button>
            </div>
          </Card>

          <RepeatCaller match={repeat} />

          {summary && (
            <Card icon={Activity} title="Result" className="good">
              <div className="grid g2 keep-2">
                <Stat value={mmss(summary.seconds_simulated)} label="Scammer time wasted (simulated)" />
                <Stat value={pctTxt(summary.entity_recall_mean)} label="Payment IDs that survived the noisy line" tone="green" />
                <Stat value={pctTxt(summary.cer_mean)} label="Character error rate (Prisma)" />
                <Stat value={summary.persona_breaks} label="Times Dadi broke character" tone={summary.persona_breaks ? "rose" : "green"} />
              </div>
              <div className="pill-src" style={{ marginTop: 10 }}>{SCAM_TYPE_LABELS[summary.scam_type] || summary.scam_type} · noise {snrLabel(summary.snr_db)}</div>
              {summary.ring_links?.length > 0 && (
                <a className="ring-alert" href="#/app/rings">
                  <Network size={16} /> Linked to {summary.ring_links.length} earlier call{summary.ring_links.length > 1 ? "s" : ""}: {summary.ring_links.map((l) => l.reason).join(" · ")}
                </a>
              )}
            </Card>
          )}

          <IntelCard intel={intel} />
        </div>

        <div className="span-7 stack">
          <Card icon={Bot} title="Live transcript" right={running === "arena" ? <span className="pulse-dot" /> : null}>
            {!feed.length && <div className="empty">Start a call to watch the AI scammer meet Dadi.</div>}
            <div className="chat" ref={feedRef}>
              {feed.map((m, i) =>
                m.speaker === "scammer" ? (
                  <div key={i} className="bubble them">
                    <div className="bubble-text"><SpeechText text={m.text || "(Prisma heard nothing)"} /></div>
                    <div className="meta">
                      Said: <span className="text-2">{m.intended}</span>
                    </div>
                    <div className="row" style={{ gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                      <Badge tone={m.cer < 0.15 ? "green" : m.cer < 0.35 ? "amber" : "rose"}>CER {pctTxt(m.cer)}</Badge>
                      {m.entity_recall != null && <Badge tone={m.entity_recall === 1 ? "green" : "rose"} dot>IDs heard {pctTxt(m.entity_recall)}</Badge>}
                      <Badge tone="muted">{snrLabel(m.snr_db)}</Badge>
                    </div>
                  </div>
                ) : (
                  <div key={i} className="bubble me">
                    <div className="bubble-text"><SpeechText text={m.text} /></div>
                    {m.tactic && <div className="meta">Tactic: {TACTIC_LABELS[m.tactic] || m.tactic}</div>}
                    {i === firstKnown && <div className="row" style={{ marginTop: 6 }}><Badge tone="rose" dot>Recognised his voice</Badge></div>}
                  </div>
                ),
              )}
            </div>
          </Card>

          <Card icon={GaugeIcon} title="Noise benchmark: can Prisma still hear the UPI ID?"
            right={<button className="btn sm" disabled={!!running} onClick={runBench}>{running === "bench" ? "Running…" : "Run benchmark"}</button>}>
            <div className="small text-2" style={{ marginBottom: 12 }}>
              6 scam lines containing UPI IDs and phone numbers, spoken by Timbre, played through an 8 kHz phone band with
              call-centre babble at each noise level, transcribed by Prisma v3.0. Uses about 30 short Gnani requests (audio is cached).
            </div>
            {!bench.rows.length && !bench.bySnr && <div className="empty">No benchmark run yet.</div>}
            {bench.rows.length > 0 && !bench.bySnr && <Hud tone="cyan">{bench.rows.length} / 30 clips transcribed…</Hud>}
            {bench.bySnr && (
              <div className="list">
                {bench.bySnr.map((r) => (
                  <div className="li" key={String(r.snr_db)} style={{ flexDirection: "column", alignItems: "stretch", gap: 6 }}>
                    <div className="row between">
                      <b>{snrLabel(r.snr_db)}</b>
                      <span className="mono small">IDs heard {pctTxt(r.entity_recall)} · CER {pctTxt(r.cer)}</span>
                    </div>
                    <Progress value={(r.entity_recall ?? 0) * 100} color="var(--green)" />
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
