import { LiveFeed } from "./components/LiveFeed";
import { MockLoginForm } from "./components/MockLoginForm";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Anomalock</h1>
        <p>ML-based login risk &amp; anomaly detection — live scoring dashboard</p>
      </header>
      <main className="app-main">
        <MockLoginForm />
        <LiveFeed />
      </main>
    </div>
  );
}
