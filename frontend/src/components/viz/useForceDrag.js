// Makes the ring radar interactive: drag any call and its linked calls follow on springs (d3-force, ISC, lazy-loaded);
// let go and everything settles back into the hand-tuned layout. The static layout is the start state and the fallback
// (reduced motion, or d3-force failing to load): nothing moves, clicks still open the report.
import { useEffect, useRef, useState } from "react";
import { reducedMotion } from "../../motion";

export function useForceDrag(home, links, svgRef) {
  const [pos, setPos] = useState(home);
  const sim = useRef(null);
  const nodes = useRef([]);
  const moved = useRef(false);
  const key = JSON.stringify(home);

  useEffect(() => {
    setPos(home);
    if (reducedMotion()) return undefined;
    let s = null, dead = false;
    import("d3-force").then(({ forceSimulation, forceLink, forceX, forceY }) => {
      if (dead) return;
      const ns = Object.entries(home).map(([id, [x, y, cx, cy]]) => ({ id, x, y, hx: x, hy: y, cx, cy }));
      nodes.current = ns;
      const ls = links.filter((l) => home[l.source] && home[l.target]).map((l) => ({ source: l.source, target: l.target }));
      s = forceSimulation(ns).velocityDecay(0.32).alphaDecay(0.045)
        .force("x", forceX((d) => d.hx).strength(0.1))
        .force("y", forceY((d) => d.hy).strength(0.1))
        .force("link", forceLink(ls).id((d) => d.id).strength(0.08).distance((l) => Math.hypot(l.source.hx - l.target.hx, l.source.hy - l.target.hy)))
        .on("tick", () => {
          if (dead) return;
          const p = {};
          ns.forEach((n) => { p[n.id] = [n.x, n.y, n.cx + (n.x - n.hx), n.cy + (n.y - n.hy)]; });
          setPos(p);
        });
      s.stop(); // idle until someone drags
      sim.current = s;
    }).catch(() => {});
    return () => { dead = true; if (s) s.stop(); sim.current = null; };
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  const toSvg = (e) => {
    const svg = svgRef.current;
    const m = svg?.getScreenCTM();
    if (!m) return { x: 0, y: 0 };
    const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
    return pt.matrixTransform(m.inverse());
  };

  const onPointerDown = (id) => (e) => {
    const s = sim.current;
    moved.current = false;
    if (!s || e.button !== 0) return;
    const n = nodes.current.find((x) => x.id === id);
    if (!n) return;
    const start = toSvg(e);
    const move = (ev) => {
      const p = toSvg(ev);
      if (!moved.current && Math.hypot(p.x - start.x, p.y - start.y) < 5) return;
      moved.current = true;
      n.fx = p.x; n.fy = p.y;
      s.alphaTarget(0.3).restart();
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      n.fx = null; n.fy = null;
      s.alphaTarget(0);
      if (moved.current) s.alpha(0.7).restart();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
  };

  // true right after a drag, so the click that ends it doesn't open the report
  const wasDragged = () => { const m = moved.current; moved.current = false; return m; };
  return { pos, onPointerDown, wasDragged };
}
