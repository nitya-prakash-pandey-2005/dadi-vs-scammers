// Recharts (MIT) donut: share of calls per scam script, with the total in the middle. Lazy-loaded chunk.
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { reducedMotion } from "../../motion";

const COLORS = ["#ff4d9d", "#a78bfa", "#22d3ee", "#fbbf24", "#34d399", "#fb7185", "#60a5fa"];

export default function ScriptDonut({ rows }) {
  const total = rows.reduce((a, r) => a + r.value, 0);
  return (
    <div className="donut">
      <div className="donut-chart">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={rows} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="92%" paddingAngle={3} stroke="none" isAnimationActive={!reducedMotion()}>
              {rows.map((r, i) => <Cell key={r.name} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip formatter={(v, n) => [`${v} call${v === 1 ? "" : "s"}`, n]}
              contentStyle={{ background: "#11152d", border: "1px solid rgba(255,255,255,0.14)", borderRadius: 10, fontSize: 12 }} itemStyle={{ color: "#e9ecf8" }} />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-mid"><b className="num">{total}</b><span>calls</span></div>
      </div>
      <div className="donut-legend">
        {rows.map((r, i) => (
          <div key={r.name}><i style={{ background: COLORS[i % COLORS.length] }} /><span>{r.name}</span><b className="mono">{r.value}</b></div>
        ))}
      </div>
    </div>
  );
}
