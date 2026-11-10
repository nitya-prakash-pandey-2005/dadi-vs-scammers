// Recharts (MIT) bar chart: seconds of scammer time each call wasted, oldest first. Lazy-loaded chunk.
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { mmss } from "../../lib/labels";
import { reducedMotion } from "../../motion";

export default function CallsChart({ calls }) {
  const data = calls.map((c, i) => ({ n: `#${i + 1}`, s: Math.round(c.wasted_seconds || 0), ids: c.intel ? Object.values(c.intel).filter(Array.isArray).length : 0 }));
  return (
    <div style={{ width: "100%", height: 190 }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id="cc-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ff7ab8" /><stop offset="1" stopColor="#8b5cf6" /></linearGradient>
          </defs>
          <XAxis dataKey="n" tick={{ fill: "#7d86a8", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#7d86a8", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => mmss(v)} width={52} />
          <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} formatter={(v) => [mmss(v), "time wasted"]}
            contentStyle={{ background: "#11152d", border: "1px solid rgba(255,255,255,0.14)", borderRadius: 10, color: "#e9ecf8", fontSize: 12 }} labelStyle={{ color: "#b7bdd8" }} />
          <Bar dataKey="s" radius={[6, 6, 2, 2]} maxBarSize={34} isAnimationActive={!reducedMotion()}>
            {data.map((d) => <Cell key={d.n} fill="url(#cc-g)" />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
