import { useEffect, useRef, useState } from "react";
import { runDemo } from "../lib/demo";
import { socket } from "../lib/socket";
import type { LiveFeedEvent } from "../lib/types";
import { PlayIcon, PulseIcon } from "./icons";

const MAX_ROWS = 100;

interface Row extends LiveFeedEvent {
  _id: number;
}

let nextRowId = 0;

export function LiveFeed() {
  const [rows, setRows] = useState<Row[]>([]);
  const [connected, setConnected] = useState(socket.connected);
  const [demoRunning, setDemoRunning] = useState(false);
  const cancelRef = useRef({ cancelled: false });

  useEffect(() => {
    function onConnect() {
      setConnected(true);
    }
    function onDisconnect() {
      setConnected(false);
    }
    function onLoginScored(payload: LiveFeedEvent) {
      setRows((prev) => [{ ...payload, _id: nextRowId++ }, ...prev].slice(0, MAX_ROWS));
    }

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("login_scored", onLoginScored);
    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("login_scored", onLoginScored);
    };
  }, []);

  useEffect(() => {
    const signal = cancelRef.current;
    signal.cancelled = false;
    const t = setTimeout(() => void startDemo(), 500);
    return () => {
      clearTimeout(t);
      signal.cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function startDemo() {
    cancelRef.current.cancelled = false;
    setDemoRunning(true);
    await runDemo(cancelRef.current);
    setDemoRunning(false);
  }

  return (
    <div className="panel feed-panel">
      <div className="feed-header">
        <h2>Live login feed</h2>
        <div className="feed-header-actions">
          <button className="replay-btn" onClick={startDemo} disabled={demoRunning}>
            <PlayIcon className="replay-icon" />
            {demoRunning ? "Replaying…" : "Replay demo"}
          </button>
          <span className={`conn-pill ${connected ? "conn-up" : "conn-down"}`}>
            <span className="conn-dot" />
            {connected ? "Live" : "Offline"}
          </span>
        </div>
      </div>
      <p className="panel-subtitle">
        Scripted demo traffic plays on load, plus anything from the mock form or{" "}
        <code>python -m api.replay</code> — all scored by the real model in real time.
      </p>

      <div className="feed-table-wrap">
        <table className="feed-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>User</th>
              <th>Location</th>
              <th>Risk</th>
              <th>Reasons</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="feed-empty">
                  <PulseIcon className="feed-empty-icon" />
                  Waking up the demo feed…
                </td>
              </tr>
            )}
            {rows.map((e) => (
              <tr key={e._id} className={`feed-row feed-row-${e.risk_level} feed-row-new`}>
                <td>{new Date(e.login_timestamp).toLocaleTimeString()}</td>
                <td className="feed-user">{e.user_id}</td>
                <td>
                  {e.city ?? "?"}, {e.country ?? "?"}
                </td>
                <td>
                  <div className="feed-risk-cell">
                    <span className="risk-badge" data-level={e.risk_level}>
                      {e.risk_score.toFixed(0)}
                    </span>
                    <span className="feed-risk-bar-track">
                      <span
                        className="feed-risk-bar-fill"
                        data-level={e.risk_level}
                        style={{ width: `${Math.max(0, Math.min(100, e.risk_score))}%` }}
                      />
                    </span>
                  </div>
                </td>
                <td className="feed-reasons">{e.flagged_reasons.map((r) => r.replaceAll("_", " ")).join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
