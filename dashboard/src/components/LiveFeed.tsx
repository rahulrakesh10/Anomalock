import { useEffect, useState } from "react";
import { socket } from "../lib/socket";
import type { LiveFeedEvent } from "../lib/types";
import { PulseIcon } from "./icons";

const MAX_ROWS = 100;

export function LiveFeed() {
  const [events, setEvents] = useState<LiveFeedEvent[]>([]);
  const [connected, setConnected] = useState(socket.connected);

  useEffect(() => {
    function onConnect() {
      setConnected(true);
    }
    function onDisconnect() {
      setConnected(false);
    }
    function onLoginScored(payload: LiveFeedEvent) {
      setEvents((prev) => [payload, ...prev].slice(0, MAX_ROWS));
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

  return (
    <div className="panel feed-panel">
      <div className="feed-header">
        <h2>Live login feed</h2>
        <span className={`conn-pill ${connected ? "conn-up" : "conn-down"}`}>
          <span className="conn-dot" />
          {connected ? "Live" : "Offline"}
        </span>
      </div>
      <p className="panel-subtitle">
        Every scored login (from the mock form, or <code>python -m api.replay</code>) appears here in real time.
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
            {events.length === 0 && (
              <tr>
                <td colSpan={5} className="feed-empty">
                  <PulseIcon className="feed-empty-icon" />
                  No events yet — try a mock login or run the replay tool.
                </td>
              </tr>
            )}
            {events.map((e, i) => (
              <tr key={i} className={`feed-row feed-row-${e.risk_level}`}>
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
                      <span className="feed-risk-bar-fill" data-level={e.risk_level} style={{ width: `${Math.max(0, Math.min(100, e.risk_score))}%` }} />
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
