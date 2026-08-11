import { useLiveStats } from "../lib/useLiveStats";

export function StatsBar() {
  const { total, high, stepUp } = useLiveStats();
  const stepUpRate = total > 0 ? Math.round((stepUp / total) * 100) : 0;

  return (
    <div className="stats-bar">
      <div className="stat-tile">
        <span className="stat-value">{total}</span>
        <span className="stat-label">Logins scored</span>
      </div>
      <div className="stat-tile">
        <span className="stat-value stat-value-high">{high}</span>
        <span className="stat-label">High risk</span>
      </div>
      <div className="stat-tile">
        <span className="stat-value stat-value-medium">{stepUp}</span>
        <span className="stat-label">Step-ups triggered</span>
      </div>
      <div className="stat-tile">
        <span className="stat-value">{stepUpRate}%</span>
        <span className="stat-label">Step-up rate</span>
      </div>
    </div>
  );
}
