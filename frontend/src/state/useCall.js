// Call state machine for the live scam line: WebSocket + mic + player + all war-room data.
import { useCallback, useEffect, useRef, useState } from "react";
import { createPcmPlayer, startMic } from "@voice/index.js";
import { openCall } from "../net/callSocket";
import { toast } from "../ui";

const RATE = 8000; // phone-quality audio both ways (Prisma is trained on 8 kHz calls)

export function useCall({ onEnded } = {}) {
  const [phase, setPhase] = useState("idle"); // idle | connecting | live | ending | ended
  const [callId, setCallId] = useState(null);
  const [persona, setPersona] = useState(null); // { key, name, city }
  const [mission, setMission] = useState(null); // { key, done }
  const [turns, setTurns] = useState([]);
  const [intel, setIntel] = useState(null);
  const [stt, setStt] = useState("idle");
  const [speaking, setSpeaking] = useState(false);
  const [startedAt, setStartedAt] = useState(null);
  const [wasted, setWasted] = useState(0);
  const [repeat, setRepeat] = useState(null); // earlier call with the same voice (Gnani voice fingerprint)
  const refs = useRef({ call: null, mic: null, player: null, onEnded });
  refs.current.onEnded = onEnded;

  const stopMic = () => {
    refs.current.mic?.stop();
    refs.current.mic = null;
  };

  const onEvent = useCallback((m) => {
    switch (m.type) {
      case "session_started":
        setCallId(m.call_id);
        setPersona({ key: m.persona, name: m.persona_name, city: m.city });
        setStartedAt(Date.now());
        setPhase("live");
        break;
      case "turn":
        setTurns((t) => [...t, m]);
        break;
      case "agent_speaking":
        setSpeaking(!!m.on);
        break;
      case "stop_audio":
        refs.current.player?.flush();
        setSpeaking(false);
        break;
      case "status":
        setStt(m.stt);
        if (m.stt === "error" && m.message) toast(m.message, "warn");
        break;
      case "intel":
        setIntel(m.intel);
        if (m.mission) setMission((old) => { if (m.mission.done && !old?.done) toast("Mission complete!", "info"); return m.mission; });
        break;
      case "repeat_caller":
        setRepeat(m.match);
        toast("Dadi knows this voice: same scammer as an earlier call", "warn");
        break;
      case "persona":
        setPersona({ key: m.persona, name: m.persona_name, city: m.city });
        toast(`${m.persona_name} took the call: language switched`, "info");
        break;
      case "call_ended":
        setCallId(m.call_id);
        setWasted(m.wasted_seconds || 0);
        setPhase("ended");
        setSpeaking(false);
        stopMic();
        refs.current.onEnded?.(m);
        break;
      default:
        break;
    }
  }, []);

  const start = useCallback(async (personaKey = "auto", noiseDb = null, missionKey = null) => {
    if (refs.current.call) return;
    setTurns([]);
    setIntel(null);
    setMission(missionKey ? { key: missionKey, done: false } : null);
    setRepeat(null);
    setWasted(0);
    setCallId(null);
    setSpeaking(false);
    setStt("connecting");
    setPhase("connecting");
    refs.current.player?.close();
    const player = createPcmPlayer({ sampleRate: RATE }); // created inside the click, so audio is allowed
    refs.current.player = player;
    const t0 = Date.now();
    refs.current.call = openCall({
      persona: personaKey,
      noiseSnrDb: noiseDb,
      mission: missionKey,
      onEvent,
      onAudio: (ab) => player.play(ab),
      onClose: () => {
        refs.current.call = null;
        stopMic();
        setStt("idle");
        setSpeaking(false);
        setPhase((p) => {
          if (p !== "ended") setWasted((w) => w || (Date.now() - t0) / 1000);
          return "ended";
        });
      },
    });
    try {
      refs.current.mic = await startMic({ targetRate: RATE, onFrame: (ab) => refs.current.call?.sendAudio(ab) });
    } catch (e) {
      toast(`Microphone unavailable: ${e?.message || e}`, "warn");
    }
  }, [onEvent]);

  const hangup = useCallback(() => {
    stopMic();
    if (refs.current.call) {
      refs.current.call.hangup();
      setPhase("ending");
    }
  }, []);

  const setNoise = useCallback((db) => refs.current.call?.setNoise(db), []);
  const playerLevel = useCallback(() => refs.current.player?.level() ?? 0, []);
  const micLevel = useCallback(() => refs.current.mic?.level() ?? 0, []);

  useEffect(() => () => {
    refs.current.call?.close();
    stopMic();
    refs.current.player?.close();
  }, []);

  return { phase, callId, persona, mission, turns, intel, repeat, stt, speaking, startedAt, wasted, start, hangup, setNoise, playerLevel, micLevel };
}

export function useNow(active, every = 250) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!active) return undefined;
    const id = setInterval(() => setNow(Date.now()), every);
    return () => clearInterval(id);
  }, [active, every]);
  return now;
}
