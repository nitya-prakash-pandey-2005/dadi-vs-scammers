// Call state machine for the live scam line: WebSocket + mic + player + all war-room data.
import { useCallback, useEffect, useRef, useState } from "react";
import { createPcmPlayer, startMic } from "@voice/index.js";
import { openCall } from "../net/callSocket";
import { toast } from "../ui";
import { DEMO, DEMO_CALL_AUDIO, DEMO_FAMILY_AUDIO } from "../demo";
import { createDemoPlayer } from "../demo/demoPlayer";

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
  const [frozenAt, setFrozenAt] = useState(null); // hang-up time: timers stop here while the server wraps up
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
        if (m.family === "handoff") toast("Dadi passed the phone to her grandson Bunty", "info");
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

  // One object per call. Async work (mic permission prompt, late socket events) checks it is still the current,
  // live call before touching shared state, so a hang-up during the prompt can never leak a mic into the next call.
  const start = useCallback(async (personaKey = "auto", noiseDb = null, missionKey = null, { speakerphone = false, family = true, replay = null } = {}) => {
    const prev = refs.current.call;
    if (prev?.live) return; // a call is already running
    prev?.sock.close(); // previous call is over but its socket is still closing
    stopMic();
    setTurns([]);
    setIntel(null);
    setMission(missionKey ? { key: missionKey, done: false } : null);
    setRepeat(null);
    setWasted(0);
    setFrozenAt(null);
    setCallId(null);
    setSpeaking(false);
    setStt("connecting");
    setPhase("connecting");
    refs.current.player?.close();
    // created inside the click, so audio is allowed (demo: the real recording of the replayed call)
    const player = DEMO ? createDemoPlayer(replay === "family" ? DEMO_FAMILY_AUDIO : DEMO_CALL_AUDIO) : createPcmPlayer({ sampleRate: RATE });
    refs.current.player = player;
    const t0 = Date.now();
    const session = { live: true, started: false, sock: null };
    const current = () => refs.current.call === session;
    refs.current.call = session;
    session.sock = openCall({
      persona: personaKey,
      noiseSnrDb: noiseDb,
      mission: missionKey,
      speakerphone,
      family,
      replay: DEMO ? replay : null,
      onEvent: (m) => {
        if (!current()) return;
        if (m.type === "session_started") {
          session.started = true;
          player.start?.(); // demo: the recording starts with the call (t = 0)
        }
        if (m.type === "call_ended") session.live = false;
        // after hang-up the server may still send intel/turns (up to ~3 s) before call_ended: keep those, but Dadi
        // must not start "speaking" again
        if (m.type === "agent_speaking" && !session.live) return;
        onEvent(m);
      },
      onAudio: (ab) => { if (current() && session.live) player.play(ab); },
      onClose: () => {
        if (!current()) return;
        session.live = false;
        refs.current.call = null;
        stopMic();
        setStt("idle");
        setSpeaking(false);
        if (!session.started) { // never reached the server (hung up while ringing, or server offline)
          player.flush();
          setPhase("idle");
          return;
        }
        setPhase((p) => {
          if (p !== "ended") setWasted((w) => w || (Date.now() - t0) / 1000);
          return "ended";
        });
      },
    });
    if (DEMO) return; // a replay needs no microphone (and must never ask for one)
    let mic;
    try {
      mic = await startMic({ targetRate: RATE, onFrame: (ab) => { if (current() && session.live) session.sock.sendAudio(ab); } });
    } catch (e) {
      if (current() && session.live) toast(`Microphone unavailable: ${e?.message || e}`, "warn");
      return;
    }
    // the call may have been hung up, ended or replaced while the permission prompt was open
    if (!current() || !session.live) {
      mic.stop();
      return;
    }
    stopMic();
    refs.current.mic = mic;
  }, [onEvent]);

  const hangup = useCallback(() => {
    stopMic();
    refs.current.player?.flush();
    refs.current.player?.stop?.(); // demo recording
    setSpeaking(false);
    const s = refs.current.call;
    if (s?.live) {
      s.live = false;
      s.sock.hangup();
      setFrozenAt(Date.now());
      setPhase("ending"); // stays "ending" until the server's call_ended (or the socket closes)
    }
  }, []);

  const setNoise = useCallback((db) => refs.current.call?.sock.setNoise(db), []);
  const playerLevel = useCallback(() => refs.current.player?.level() ?? 0, []);
  const micLevel = useCallback(() => refs.current.mic?.level() ?? 0, []);

  useEffect(() => () => {
    refs.current.call?.sock.close();
    refs.current.call = null;
    stopMic();
    refs.current.player?.close();
  }, []);

  return { phase, callId, persona, mission, turns, intel, repeat, stt, speaking, startedAt, frozenAt, wasted, start, hangup, setNoise, playerLevel, micLevel };
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
