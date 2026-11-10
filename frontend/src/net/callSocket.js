// WebSocket client for /ws/call (protocol: backend/dadi/app.py).
import { DEMO } from "../demo";
import { DemoSocket } from "../demo/DemoSocket";

// openCall({ persona, noiseSnrDb, mission, speakerphone, family, onEvent, onAudio, onClose }) -> { sendAudio, setNoise, hangup, close }

export function openCall({ persona = "auto", noiseSnrDb = null, mission = null, speakerphone = false, family = true, replay = null, onEvent, onAudio, onClose } = {}) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${window.location.host}/ws/call`;
  const ws = DEMO ? new DemoSocket(url) : new WebSocket(url); // demo: replays a recorded call
  ws.binaryType = "arraybuffer";
  let closed = false;
  let aborted = false; // hung up before the socket opened: never send "start"

  ws.onopen = () => {
    if (aborted) {
      try { ws.close(); } catch { /* already closed */ }
      return;
    }
    const start = { type: "start", persona, noise_snr_db: noiseSnrDb, mission, family: family !== false }; // family hand-off to Bunty
    if (replay) start.replay = replay; // demo build: which recorded call to replay
    if (speakerphone) start.speakerphone = true; // backend switches to half-duplex (older backends ignore it)
    ws.send(JSON.stringify(start));
  };
  ws.onmessage = (e) => {
    if (aborted) return;
    if (typeof e.data === "string") {
      try { onEvent?.(JSON.parse(e.data)); } catch { /* ignore malformed */ }
    } else {
      onAudio?.(e.data);
    }
  };
  ws.onerror = () => {
    if (!aborted) onEvent?.({ type: "status", stt: "error", message: "Connection to the Dadi server failed" });
  };
  ws.onclose = () => {
    if (closed) return;
    closed = true;
    onClose?.();
  };

  const isOpen = () => ws.readyState === WebSocket.OPEN;
  return {
    sendAudio(ab) {
      // drop audio rather than queue it up on a slow network (realtime beats completeness)
      if (!aborted && isOpen() && ws.bufferedAmount < 256 * 1024) ws.send(ab);
    },
    setNoise(db) {
      if (!aborted && isOpen()) ws.send(JSON.stringify({ type: "set_noise", snr_db: db }));
    },
    hangup() {
      if (ws.readyState === WebSocket.CONNECTING) aborted = true; // onopen closes it without starting a session
      else if (isOpen()) ws.send(JSON.stringify({ type: "hangup" }));
      // the server sends call_ended within ~3 s (pending intel finishes first); close anyway if it never comes
      setTimeout(() => { try { ws.close(); } catch { /* already closed */ } }, 8000);
    },
    close() {
      aborted = true;
      if (ws.readyState === WebSocket.CONNECTING) return; // onopen closes it (avoids a console error)
      try { ws.close(); } catch { /* already closed */ }
    },
  };
}
