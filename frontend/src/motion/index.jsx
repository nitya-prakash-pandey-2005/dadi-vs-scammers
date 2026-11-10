// One motion helper for the whole app (anime.js v4). Rules: transform/opacity only, never block input,
// and when the user prefers reduced motion every helper jumps straight to the final state.
import { useEffect, useRef, useState } from "react";
import { animate, stagger, utils } from "animejs";
import "./motion.css";

export const reducedMotion = () =>
  typeof window !== "undefined" && !!window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// `motion-ok` gates every "hidden until revealed" style, so no-JS and reduced-motion users always see the content.
if (typeof document !== "undefined" && !reducedMotion()) document.documentElement.classList.add("motion-ok");

export const EASE = "outExpo";

// Animate a number from `from` to `to`, writing the formatted value into el.textContent.
export function countUp(el, to, { from = 0, duration = 1600, decimals = 0, format, delay = 0 } = {}) {
  const fmt = format || ((v) => v.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }));
  if (!el) return null;
  if (reducedMotion() || from === to) { el.textContent = fmt(to); return null; }
  const o = { v: from };
  el.textContent = fmt(from);
  return animate(o, { v: to, duration, delay, ease: "outExpo", onUpdate: () => { el.textContent = fmt(o.v); }, onComplete: () => { el.textContent = fmt(to); } });
}

// Run `fn` once, the first time `el` scrolls into view.
export function onceVisible(el, fn, { margin = "0px 0px -12% 0px", threshold = 0.15 } = {}) {
  if (!el) return () => {};
  if (typeof IntersectionObserver === "undefined") { fn(); return () => {}; }
  const io = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) { io.disconnect(); fn(); }
  }, { rootMargin: margin, threshold });
  io.observe(el);
  return () => io.disconnect();
}

// Staggered reveal of `selector` inside `root` when it scrolls into view.
export function revealOnScroll(root, selector = "[data-reveal]", { y = 28, gap = 70, duration = 900 } = {}) {
  if (!root) return () => {};
  const els = [...root.querySelectorAll(selector)];
  const show = () => els.forEach((e) => e.classList.add("is-in"));
  if (reducedMotion()) { show(); return () => {}; }
  return onceVisible(root, () => {
    animate(els, {
      opacity: [0, 1], translateY: [y, 0], duration, delay: stagger(gap), ease: EASE,
      onBegin: show,
      onComplete: (a) => utils.cleanInlineStyles(a),
    });
  });
}

// <CountUp to={156} /> : counts up from 0 on mount and to each new value afterwards (respects reduced motion).
export function CountUp({ to, decimals = 0, format, duration = 1100 }) {
  const ref = useRef(null);
  const last = useRef(0);
  const [initial] = useState(() => (reducedMotion() ? to : 0));
  const fmt = format || ((v) => Number(v).toFixed(decimals));
  useEffect(() => {
    const a = countUp(ref.current, to, { from: last.current, decimals, format: fmt, duration });
    last.current = to;
    return () => { if (a) a.pause(); };
  }, [to]); // eslint-disable-line react-hooks/exhaustive-deps
  return <span ref={ref}>{fmt(initial)}</span>;
}

// App-wide motion: a short fade/slide of the page on every route change. Called once from the AppShell.
export function useRouteMotion(path) {
  useEffect(() => {
    if (reducedMotion()) return undefined;
    const el = document.querySelector(".shell .content");
    if (!el) return undefined;
    const a = animate(el, {
      opacity: [0, 1], translateY: [10, 0], duration: 420, ease: "outCubic",
      onComplete: (x) => utils.cleanInlineStyles(x),
    });
    return () => { a.pause(); utils.cleanInlineStyles(a); };
  }, [path]);
}
