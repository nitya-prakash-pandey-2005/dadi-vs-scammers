import { useState } from "react";
import { PhoneCall, Radar } from "lucide-react";
import { PageHead } from "../ui";
import Phone from "../components/Phone";
import WarRoom from "../components/WarRoom";

export default function CallRoom({ call, personas, totals, personaKey, setPersonaKey, noise, setNoise }) {
  const [tab, setTab] = useState("phone"); // only used under 900px
  return (
    <>
      <PageHead
        kicker="Dadi vs Scammers"
        title="Don't block scammers. Route them to Dadi."
        sub="An AI grandmother on Gnani Prisma (speech-to-text) and Timbre (voice) keeps scam callers busy in Hinglish, Tanglish and Benglish, and pulls out their mule accounts."
      />
      <div className="tabs-line callroom-tabs" role="tablist">
        <button className={tab === "phone" ? "on" : ""} onClick={() => setTab("phone")}><PhoneCall size={15} /> Phone</button>
        <button className={tab === "war" ? "on" : ""} onClick={() => setTab("war")}><Radar size={15} /> War room</button>
      </div>
      <div className="callroom">
        <div className="phone-col" data-hidden={tab !== "phone"}>
          <Phone call={call} personas={personas} personaKey={personaKey} setPersonaKey={setPersonaKey} noise={noise} setNoise={setNoise} />
        </div>
        <div className="war-col" data-hidden={tab !== "war"}>
          <WarRoom call={call} totals={totals} />
        </div>
      </div>
    </>
  );
}
