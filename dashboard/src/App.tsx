import { LiveFeed } from "./components/LiveFeed";
import { MockLoginForm } from "./components/MockLoginForm";
import { StatsBar } from "./components/StatsBar";
import { ShieldIcon } from "./components/icons";

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
        <StatsBar />
      </header>
      <main className="app-main">
        <MockLoginForm />
        <LiveFeed />
      </main>
    </div>
  );
}
