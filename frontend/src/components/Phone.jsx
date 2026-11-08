import { useEffect, useRef } from "react";
import { Headphones, PhoneCall, PhoneOff, ShieldAlert } from "lucide-react";
import { Badge, Card, Hud, Seg, hueOf, initials } from "../ui";
import { DISCLAIMER, MIX_LABEL, PERSONA_HUE, mmss } from "../lib/labels";
import { useNow } from "../state/useCall";

const NOISE_OPTIONS = [
  { value: "off", label: "Off" },
  { value: "20", label: "20 dB" },
  { value: "10", label: "10 dB" },
  { value: "5", label: "5 dB" },
  { value: "0", label: "0 dB" },
];
const STT_BADGE = {
  idle: ["muted", "Line idle"],
  connecting: ["cyan", "Connecting…"],
  connected: ["green", "Prisma listening"],
  reconnecting: ["amber", "Reconnecting…"],
  error: ["rose", "Speech service error"],
};
const SHORT = { dadi: "Dadi", paati: "Paati", thakuma: "Thakuma" };

export const noiseToDb = (v) => (v === "off" ? null : Number(v));

export default function Phone({ call, personas, personaKey, setPersonaKey, noise, setNoise }) {
  const live = ["connecting", "live", "ending"].includes(call.phase);
  const now = useNow(live);
  const elapsed = live && call.startedAt ? (now - call.startedAt) / 1000 : call.phase === "ended" ? call.wasted : 0;
  const ringRef = useRef(null);

  const chosen = personas.find((p) => p.key === (personaKey === "auto" ? "dadi" : personaKey));
  const shown = call.persona?.name ? call.persona : chosen ? { key: chosen.key, name: chosen.name, city: chosen.city } : null;
  const lang = personas.find((p) => p.key === shown?.key)?.language;
  const [tone, label] = STT_BADGE[call.stt] || STT_BADGE.idle;

  // avatar ring pulses with Dadi's voice level (DOM writes, no re-renders)
  useEffect(() => {
    if (!live) {
      if (ringRef.current) ringRef.current.style.transform = "scale(1)";
      return undefined;
    }
    let raf;
    const tick = () => {
      const lv = call.playerLevel();
      if (ringRef.current) {
        ringRef.current.style.transform = `scale(${1 + lv * 0.18})`;
        ringRef.current.style.opacity = String(0.75 + lv * 0.25);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [live, call.playerLevel]);

  const changeNoise = (v) => {
    setNoise(v);
    if (live) call.setNoise(noiseToDb(v));
  };

  return (
    <Card className="phone glow" tour="phone">
      <div className="row between">
        <Hud tone="pink">Scam line</Hud>
        <Badge tone={tone} dot>{label}</Badge>
      </div>

      <div className="avatar-wrap">
        <div className={`ring ${live ? "live" : ""}`} ref={ringRef}>
          <div className="face" style={{ background: hueOf(PERSONA_HUE[shown?.key] ?? 330) }}>
            {initials(shown?.name || "Dadi")}
          </div>
        </div>
      </div>

      <div className="who">
        <b>{shown?.name || "Dadi"}</b>
        <div className="small muted">
          {shown?.city ? `${shown.city} · ` : ""}{MIX_LABEL[lang] || "Hinglish"}
          {personaKey === "auto" && call.phase === "idle" ? " · auto-switches by language" : ""}
        </div>
        <div className="call-timer">
          {call.phase === "idle" && "Ready"}
          {call.phase === "connecting" && "Ringing…"}
          {(call.phase === "live" || call.phase === "ending") && <>{call.speaking ? "Speaking · " : "On call · "}{mmss(elapsed)}</>}
          {call.phase === "ended" && <>Call ended · {mmss(call.wasted)}</>}
        </div>
      </div>

      {live ? (
        <button className="btn danger lg block" onClick={call.hangup} disabled={call.phase === "ending"}>
          <PhoneOff size={18} /> {call.phase === "ending" ? "Hanging up…" : "Hang up"}
        </button>
      ) : (
        <button className="btn primary lg block" onClick={() => call.start(personaKey, noiseToDb(noise))}>
          <PhoneCall size={18} /> Call {personaKey === "auto" ? "Dadi" : SHORT[personaKey] || "Dadi"}
        </button>
      )}

      <div className="field">
        <span>Who picks up</span>
        <div className={live ? "locked" : ""}>
          <Seg
            options={[{ value: "auto", label: "Auto" }, ...personas.map((p) => ({ value: p.key, label: SHORT[p.key] || p.name }))]}
            value={personaKey}
            onChange={setPersonaKey}
          />
        </div>
      </div>

      <div className="field">
        <span>Call-centre noise (SNR)</span>
        <Seg options={NOISE_OPTIONS} value={noise} onChange={changeNoise} />
        <span className="pill-src">Mixes Gnani-voiced call-centre babble into the scammer's audio before Prisma hears it</span>
      </div>

      <div className="callout">
        <Headphones size={18} className="flex-none" />
        <span>Use earphones while playing the scammer, so Dadi doesn't hear herself.</span>
      </div>

      <div className="disclaimer">
        <ShieldAlert size={15} className="flex-none" />
        <span>{DISCLAIMER}</span>
      </div>
    </Card>
  );
}
