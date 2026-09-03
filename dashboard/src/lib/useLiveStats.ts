import { useEffect, useState } from "react";
import { socket } from "./socket";
import type { LiveFeedEvent, RiskLevel } from "./types";

export interface HistoryPoint {
  id: number;
  score: number;
  level: RiskLevel;
}

export interface LiveStats {
  total: number;
  high: number;
  medium: number;
  low: number;
  stepUp: number;
  /** Rolling window of recent scores, oldest first — feeds the sparkline. */
  history: HistoryPoint[];
}

const HISTORY_SIZE = 40;
let nextId = 0;

const EMPTY: LiveStats = { total: 0, high: 0, medium: 0, low: 0, stepUp: 0, history: [] };

/** Runs totals across everything scored this session, independent of the
 * feed's own trimmed row list, so the header stats never reset just
 * because old rows scrolled out of view. */
export function useLiveStats(): LiveStats {
  const [stats, setStats] = useState<LiveStats>(EMPTY);

  useEffect(() => {
    function onLoginScored(payload: LiveFeedEvent) {
      setStats((prev) => ({
        total: prev.total + 1,
        high: prev.high + (payload.risk_level === "high" ? 1 : 0),
        medium: prev.medium + (payload.risk_level === "medium" ? 1 : 0),
        low: prev.low + (payload.risk_level === "low" ? 1 : 0),
        stepUp: prev.stepUp + (payload.step_up_required ? 1 : 0),
        history: [...prev.history, { id: nextId++, score: payload.risk_score, level: payload.risk_level }].slice(
          -HISTORY_SIZE
        ),
      }));
    }
    socket.on("login_scored", onLoginScored);
    return () => {
      socket.off("login_scored", onLoginScored);
    };
  }, []);

  return stats;
}
