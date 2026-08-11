import type { RiskLevel } from "../lib/types";

export function RiskMeter({ score, level }: { score: number; level: RiskLevel }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="risk-meter">
      <div className="risk-meter-track">
        <div className="risk-meter-fill" data-level={level} style={{ width: `${pct}%` }} />
      </div>
      <div className="risk-meter-labels">
        <span>0</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  );
}
