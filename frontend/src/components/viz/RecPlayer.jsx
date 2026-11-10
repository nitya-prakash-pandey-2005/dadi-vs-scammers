// Call recording player: the native <audio> stays (keyboard, print, fallback), and wavesurfer.js (BSD-3, lazy-loaded)
// draws the stereo recording as two waveforms on top of it: caller (left channel) and Dadi (right channel).
import { useEffect, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";

export default function RecPlayer({ src, persona = "Dadi" }) {
  const audio = useRef(null);
  const box = useRef(null);
  const [ready, setReady] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let ws = null, dead = false;
    import("wavesurfer.js").then(({ default: WaveSurfer }) => {
      if (dead || !box.current || !audio.current) return;
      ws = WaveSurfer.create({
        container: box.current, media: audio.current, url: src, height: 44, barWidth: 2, barGap: 1.5, barRadius: 2,
        cursorColor: "#ffffff", cursorWidth: 1.5, normalize: true, dragToSeek: true,
        splitChannels: [
          { waveColor: "rgba(251, 113, 133, 0.45)", progressColor: "#fb7185" },
          { waveColor: "rgba(167, 139, 250, 0.45)", progressColor: "#ff7ab8" },
        ],
      });
      ws.on("ready", () => !dead && setReady(true));
      ws.on("play", () => !dead && setPlaying(true));
      ws.on("pause", () => !dead && setPlaying(false));
      ws.on("error", () => !dead && setFailed(true));
    }).catch(() => setFailed(true));
    return () => { dead = true; if (ws) ws.destroy(); };
  }, [src]);

  return (
    <div className={`recp ${ready ? "ready" : ""} ${failed ? "failed" : ""}`}>
      {!failed && (
        <div className="recp-wave no-print">
          <button type="button" className="recp-btn" disabled={!ready} aria-label={playing ? "Pause recording" : "Play recording"}
            onClick={() => { const a = audio.current; if (a) (a.paused ? a.play() : a.pause()); }}>
            {playing ? <Pause size={18} /> : <Play size={18} />}
          </button>
          <div className="recp-tracks">
            <div className="recp-legend"><span className="c1">Caller (left)</span><span className="c2">{persona} (right)</span></div>
            <div ref={box} className="recp-box">{!ready && <div className="skeleton" style={{ height: 88 }} />}</div>
          </div>
        </div>
      )}
      <audio ref={audio} className="rec-player no-print" controls preload="metadata" src={src} crossOrigin="anonymous" />
    </div>
  );
}
