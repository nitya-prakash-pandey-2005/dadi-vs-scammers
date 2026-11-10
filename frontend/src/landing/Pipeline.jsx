// Animated architecture diagram: the paths draw themselves in, then pulses travel along them (anime.js svg helpers).
// Two layouts: wide (desktop) and tall (phones), so labels never shrink below a readable size.
import { useEffect, useRef } from "react";
import { animate, stagger, svg } from "animejs";
import { onceVisible, reducedMotion } from "../motion";

const WIDE = {
  vb: "0 0 940 430",
  nodes: [
    { x: 20, y: 160, w: 160, h: 80, t: "Scammer's call", s: "8 kHz phone audio", tone: "rose" },
    { x: 270, y: 160, w: 160, h: 80, t: "Gnani Prisma v3.0", s: "streaming STT · codemix", tone: "cyan", gn: 1 },
    { x: 520, y: 160, w: 160, h: 80, t: "Tactic planner + LLM", s: "mishear · “trying to pay”", tone: "violet" },
    { x: 770, y: 160, w: 160, h: 80, t: "Gnani Timbre v3.0", s: "streaming TTS · <coughs>", tone: "pink", gn: 1 },
    { x: 270, y: 335, w: 160, h: 70, t: "Voice fingerprint", s: "repeat caller · ring radar", tone: "cyan", out: 1 },
    { x: 520, y: 335, w: 160, h: 70, t: "Intel + complaint", s: "UPI · account · IFSC → 1930", tone: "violet", out: 1 },
    { x: 770, y: 335, w: 160, h: 70, t: "Evidence pack", s: "2-track WAV · SHA-256", tone: "pink", out: 1 },
  ],
  main: ["M180 200 H270", "M430 200 H520", "M680 200 H770", "M850 160 V78 Q850 56 828 56 H122 Q100 56 100 78 V160"],
  branch: ["M350 240 V335", "M600 240 V335", "M850 240 V335"],
  label: { x: 475, y: 44, t: "Dadi answers in her own voice, in his language" },
};

const TALL = {
  vb: "0 0 360 770",
  nodes: [
    { x: 90, y: 20, w: 220, h: 72, t: "Scammer's call", s: "8 kHz phone audio", tone: "rose" },
    { x: 90, y: 140, w: 220, h: 72, t: "Gnani Prisma v3.0", s: "streaming STT · codemix", tone: "cyan", gn: 1 },
    { x: 90, y: 260, w: 220, h: 72, t: "Tactic planner + LLM", s: "mishear · “trying to pay”", tone: "violet" },
    { x: 90, y: 380, w: 220, h: 72, t: "Gnani Timbre v3.0", s: "streaming TTS · <coughs>", tone: "pink", gn: 1 },
    { x: 90, y: 520, w: 220, h: 62, t: "Voice fingerprint", s: "repeat caller · ring radar", tone: "cyan", out: 1 },
    { x: 90, y: 604, w: 220, h: 62, t: "Intel + complaint", s: "UPI · account · IFSC → 1930", tone: "violet", out: 1 },
    { x: 90, y: 688, w: 220, h: 62, t: "Evidence pack", s: "2-track WAV · SHA-256", tone: "pink", out: 1 },
  ],
  main: ["M200 92 V140", "M200 212 V260", "M200 332 V380", "M90 416 H60 Q40 416 40 396 V76 Q40 56 60 56 H90"],
  branch: ["M200 452 V520", "M310 296 H334 V635 H310", "M200 582 V604"],
  label: null,
};

const TONE = { rose: "#fb7185", cyan: "#22d3ee", violet: "#a78bfa", pink: "#ff7ab8" };

function Diagram({ L, className }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || reducedMotion()) return undefined;
    const anims = [];
    const stop = onceVisible(el, () => {
      const lines = svg.createDrawable(el.querySelectorAll(".p-path"));
      anims.push(animate(lines, { draw: ["0 0", "0 1"], duration: 1400, delay: stagger(140), ease: "inOutQuad" }));
      anims.push(animate(el.querySelectorAll(".p-node"), { opacity: [0, 1], scale: [0.9, 1], duration: 700, delay: stagger(90), ease: "outBack(1.4)" }));
      el.querySelectorAll(".p-pulse").forEach((dot, i) => {
        const path = el.querySelector(`#${dot.dataset.for}`);
        if (!path) return;
        const mp = svg.createMotionPath(path);
        anims.push(animate(dot, { ...mp, opacity: [0, 1, 1, 0], duration: dot.dataset.long ? 3200 : 1500, delay: 1200 + i * 260, loop: true, loopDelay: 600, ease: "inOutSine" }));
      });
    }, { threshold: 0.25 });
    return () => { stop(); anims.forEach((a) => a.pause()); };
  }, []);
  const id = className;
  return (
    <svg ref={ref} className={`l-pipe ${className}`} viewBox={L.vb} role="img" aria-label="Pipeline: the scammer's call goes to Gnani Prisma v3.0 speech-to-text, then a tactic planner and LLM, then Gnani Timbre v3.0 speaks Dadi's reply back to the caller; the call also produces a voice fingerprint, intel with a complaint draft, and a sealed evidence pack.">
      <defs>
        <linearGradient id={`${id}-g`} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2={L.vb.split(" ")[2]} y2={L.vb.split(" ")[3]}><stop offset="0" stopColor="#ff4d9d" /><stop offset=".5" stopColor="#a855f7" /><stop offset="1" stopColor="#22d3ee" /></linearGradient>
        <filter id={`${id}-glow`} x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
      </defs>
      {L.main.map((d, i) => <path key={`m${i}`} id={`${id}-m${i}`} className="p-path" d={d} stroke={`url(#${id}-g)`} />)}
      {L.branch.map((d, i) => <path key={`b${i}`} id={`${id}-b${i}`} className="p-path dash" d={d} />)}
      {L.label && <text x={L.label.x} y={L.label.y} textAnchor="middle" className="p-label">{L.label.t}</text>}
      {L.nodes.map((n, i) => (
        <g key={i} className="p-node" style={{ transformOrigin: `${n.x + n.w / 2}px ${n.y + n.h / 2}px`, transformBox: "view-box" }}>
          <rect x={n.x} y={n.y} width={n.w} height={n.h} rx="14" className={`p-box ${n.out ? "out" : ""}`} style={{ stroke: TONE[n.tone] }} />
          {n.gn ? <text x={n.x + n.w - 12} y={n.y + 18} textAnchor="end" className="p-gn">GNANI</text> : null}
          <text x={n.x + n.w / 2} y={n.y + n.h / 2 - 3} textAnchor="middle" className="p-t" style={{ fill: TONE[n.tone] }}>{n.t}</text>
          <text x={n.x + n.w / 2} y={n.y + n.h / 2 + 16} textAnchor="middle" className="p-s">{n.s}</text>
        </g>
      ))}
      {L.main.map((_, i) => <circle key={`pm${i}`} r="5" className="p-pulse" data-for={`${id}-m${i}`} data-long={i === 3 ? 1 : undefined} filter={`url(#${id}-glow)`} cx="0" cy="0" />)}
      {L.branch.map((_, i) => <circle key={`pb${i}`} r="4" className="p-pulse alt" data-for={`${id}-b${i}`} filter={`url(#${id}-glow)`} cx="0" cy="0" />)}
    </svg>
  );
}

export default function Pipeline() {
  return (
    <div className="l-pipe-wrap">
      <Diagram L={WIDE} className="wide" />
      <Diagram L={TALL} className="tall" />
    </div>
  );
}
