import { useLiveStats } from "../lib/useLiveStats";
import { ChartIcon } from "./icons";

const LEVEL_COLOR: Record<string, string> = {
  low: "var(--low)",
  medium: "var(--medium)",
  high: "var(--high)",
};

const SPARK_W = 100;
const SPARK_H = 100;

function Sparkline({ points }: { points: { id: number; score: number; level: string }[] }) {
  if (points.length < 2) {
    return <div className="spark-empty">Score history appears here once a few logins are scored.</div>;
  }

  const step = SPARK_W / (points.length - 1);
  const coords = points.map((p, i) => ({ x: i * step, y: SPARK_H - (p.score / 100) * SPARK_H, p }));
  const line = coords.map((c) => `${c.x.toFixed(2)},${c.y.toFixed(2)}`).join(" ");
  const area = `0,${SPARK_H} ${line} ${SPARK_W},${SPARK_H}`;

  return (
    <svg className="sparkline" viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} preserveAspectRatio="none">
      <polygon points={area} className="spark-area" />
      <polyline points={line} className="spark-line" />
      {coords.map((c) => (
        <circle key={c.p.id} cx={c.x} cy={c.y} r={1.6} fill={LEVEL_COLOR[c.p.level]} />
      ))}
    </svg>
  );
}

export function AnalyticsPanel() {
  const { total, low, medium, high, history } = useLiveStats();

  const bars: { key: string; label: string; count: number; color: string }[] = [
    { key: "low", label: "Low", count: low, color: "var(--low)" },
    { key: "medium", label: "Medium", count: medium, color: "var(--medium)" },
    { key: "high", label: "High", count: high, color: "var(--high)" },
  ];

  return (
    <div className="panel analytics-panel">
      <div className="panel-title-row">
        <ChartIcon className="panel-title-icon" />
        <h2>Risk overview</h2>
      </div>
      <p className="panel-subtitle">Live distribution and score trend across everything scored this session.</p>

      <div className="spark-wrap">
        <Sparkline points={history} />
      </div>

      <div className="dist-bars">
        {bars.map((b) => {
          const pct = total > 0 ? Math.round((b.count / total) * 100) : 0;
          return (
            <div className="dist-row" key={b.key}>
              <span className="dist-label">{b.label}</span>
              <div className="dist-track">
                <div className="dist-fill" style={{ width: `${pct}%`, background: b.color }} />
              </div>
              <span className="dist-count">{b.count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
