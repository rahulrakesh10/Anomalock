import { useState, type FC } from "react";
import { scoreLogin } from "../lib/api";
import { buildScenarioEvents, SCENARIOS, type ScenarioKey } from "../lib/scenarios";
import type { ScoreOut } from "../lib/types";
import { DeviceSwitchIcon, PlaneIcon, UserCheckIcon } from "./icons";
import { RiskMeter } from "./RiskMeter";

const SCENARIO_ICONS: Record<ScenarioKey, FC<{ className?: string }>> = {
  normal: UserCheckIcon,
  new_device: DeviceSwitchIcon,
  impossible_travel: PlaneIcon,
};

export function MockLoginForm() {
  const [userId, setUserId] = useState("demo.user");
  const [loading, setLoading] = useState<ScenarioKey | null>(null);
  const [result, setResult] = useState<ScoreOut | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const [mfaVerified, setMfaVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runScenario(key: ScenarioKey) {
    setLoading(key);
    setError(null);
    setResult(null);
    setMfaVerified(false);
    setMfaCode("");
    try {
      const { seed, actual } = buildScenarioEvents(key, userId.trim() || "demo.user");
      await scoreLogin(seed); // quietly establishes baseline history, not shown
      const scored = await scoreLogin(actual);
      setResult(scored);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="panel">
      <h2>Mock login</h2>
      <p className="panel-subtitle">Pick a scenario to see how Anomalock scores it and whether it triggers step-up auth.</p>

      <label className="field-label" htmlFor="user_id">
        Username
      </label>
      <input id="user_id" className="text-input" value={userId} onChange={(e) => setUserId(e.target.value)} />

      <div className="scenario-buttons">
        {SCENARIOS.map((s) => {
          const Icon = SCENARIO_ICONS[s.key];
          return (
            <button
              key={s.key}
              className="scenario-btn"
              data-scenario={s.key}
              disabled={loading !== null}
              onClick={() => runScenario(s.key)}
            >
              <span className="scenario-icon">
                <Icon />
              </span>
              <span className="scenario-text">
                <span className="scenario-label">{loading === s.key ? "Scoring…" : s.label}</span>
                <span className="scenario-desc">{s.description}</span>
              </span>
            </button>
          );
        })}
      </div>

      {error && <div className="error-box">{error}</div>}

      {result && (
        <div className={`result-panel result-${result.risk_level}`}>
          <div className="result-header">
            <span className="risk-badge" data-level={result.risk_level}>
              {result.risk_level.toUpperCase()}
            </span>
            <span className="risk-score">{result.risk_score.toFixed(1)} / 100</span>
          </div>

          <RiskMeter score={result.risk_score} level={result.risk_level} />

          {result.flagged_reasons.length > 0 && (
            <ul className="reasons-list">
              {result.flagged_reasons.map((r) => (
                <li key={r}>{r.replaceAll("_", " ")}</li>
              ))}
            </ul>
          )}

          {result.step_up_required ? (
            mfaVerified ? (
              <div className="step-up-success">✓ Step-up verification passed. Access granted.</div>
            ) : (
              <div className="step-up-box">
                <div className="step-up-title">Step-up authentication required</div>
                <p>This login looked risky enough that a real system would ask for a second factor before letting it through.</p>
                <input
                  className="text-input"
                  placeholder="Enter 6-digit code (any value works — this is a mock)"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                />
                <button className="verify-btn" disabled={!mfaCode} onClick={() => setMfaVerified(true)}>
                  Verify
                </button>
              </div>
            )
          ) : (
            <div className="login-success">✓ Login successful — no step-up required.</div>
          )}
        </div>
      )}
    </div>
  );
}
