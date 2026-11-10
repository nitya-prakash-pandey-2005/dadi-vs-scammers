import { useEffect, useState } from "react";
import { PhoneCall, PhoneOff, Radar } from "lucide-react";
import { PageHead } from "../ui";
import Phone from "../components/Phone";
import WarRoom from "../components/WarRoom";
import { useNow } from "../state/useCall";
import { mmss } from "../lib/labels";

// Phones only (CSS): the war room tab keeps a small call bar, so the caller can watch the transcript and still hang up.
function MiniCallBar({ call }) {
  const live = ["connecting", "live", "ending"].includes(call.phase);
  const now = useNow(live);
  if (!live) return null;
  const secs = call.startedAt ? (now - call.startedAt) / 1000 : 0;
  const who = call.persona?.name || "Dadi";
  return (
    <div className="minibar" role="status">
      <span className="pulse-dot" />
      <span className="grow">
        {call.phase === "connecting" ? "Ringing…" : `${call.speaking ? `${who} speaking` : "On call"} · ${mmss(secs)}`}
      </span>
      <button className="btn danger sm" onClick={call.hangup} disabled={call.phase === "ending"} aria-label="Hang up">
        <PhoneOff size={15} /> {call.phase === "ending" ? "Hanging up…" : "Hang up"}
      </button>
    </div>
  );
}

export default function CallRoom({ call, personas, totals, personaKey, setPersonaKey, noise, setNoise }) {
  const [tab, setTab] = useState("phone"); // only used under 900px
  // on a phone, jump to the war room once the call connects (the call bar there still has "Hang up")
  useEffect(() => { if (call.phase === "live") setTab("war"); }, [call.phase]);
  return (
    <>
      <PageHead
        kicker="Dadi vs Scammers"
        title="Don't block scammers. Route them to Dadi."
        sub="An AI grandmother on Gnani Prisma (speech-to-text) and Timbre (voice) keeps scam callers busy in Hinglish, Tanglish and Benglish, and pulls out their mule accounts."
      />
      <div className="tabs-line callroom-tabs" role="tablist">
        <button role="tab" aria-selected={tab === "phone"} className={tab === "phone" ? "on" : ""} onClick={() => setTab("phone")}><PhoneCall size={15} /> Phone</button>
        <button role="tab" aria-selected={tab === "war"} className={tab === "war" ? "on" : ""} onClick={() => setTab("war")}><Radar size={15} /> War room</button>
      </div>
      <div className="callroom">
        <div className="phone-col" data-hidden={tab !== "phone"}>
          <Phone call={call} personas={personas} personaKey={personaKey} setPersonaKey={setPersonaKey} noise={noise} setNoise={setNoise} />
        </div>
        <div className="war-col" data-hidden={tab !== "war"}>
          <MiniCallBar call={call} />
          <WarRoom call={call} totals={totals} />
        </div>
      </div>
    </>
  );
}
