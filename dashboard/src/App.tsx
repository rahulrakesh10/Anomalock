import { AnalyticsPanel } from "./components/AnalyticsPanel";
import { LiveFeed } from "./components/LiveFeed";
import { MockLoginForm } from "./components/MockLoginForm";
import { StatsBar } from "./components/StatsBar";
import { ShieldIcon } from "./components/icons";

const STACK = ["Python", "scikit-learn", "FastAPI", "PostgreSQL", "React", "Socket.IO", "Docker", "Fly.io"];

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">
            <ShieldIcon />
          </span>
          <div>
            <h1>Anomalock</h1>
            <p>ML-based login risk &amp; anomaly detection — live scoring dashboard</p>
          </div>
        </div>
        <div className="header-right">
          <div className="sys-status">
            <span className="sys-status-dot" />
            Model: Isolation Forest · Live
          </div>
          <StatsBar />
        </div>
      </header>
      <main className="app-main">
        <MockLoginForm />
        <div className="app-main-right">
          <AnalyticsPanel />
          <LiveFeed />
        </div>
      </main>
      <footer className="app-footer">
        <div className="footer-stack">
          {STACK.map((s) => (
            <span className="stack-chip" key={s}>
              {s}
            </span>
          ))}
        </div>
        <div className="footer-links">
          <a href="https://github.com/rahulrakesh10/Anomalock" target="_blank" rel="noreferrer">
            Source on GitHub
          </a>
          <span className="footer-sep">·</span>
          <a href="https://github.com/rahulrakesh10/Anomalock/blob/main/reports/model_comparison.md" target="_blank" rel="noreferrer">
            Model comparison report
          </a>
        </div>
      </footer>
    </div>
  );
}
