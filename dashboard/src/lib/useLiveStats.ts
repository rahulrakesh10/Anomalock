import { useEffect, useState } from "react";
import { socket } from "./socket";
import type { LiveFeedEvent } from "./types";

export interface LiveStats {
  total: number;
  high: number;
  stepUp: number;
}

/** Runs totals across everything scored this session, independent of the
 * feed's own trimmed row list, so the header stats never reset just
 * because old rows scrolled out of view. */
export function useLiveStats(): LiveStats {
  const [stats, setStats] = useState<LiveStats>({ total: 0, high: 0, stepUp: 0 });

  useEffect(() => {
    function onLoginScored(payload: LiveFeedEvent) {
      setStats((prev) => ({
        total: prev.total + 1,
        high: prev.high + (payload.risk_level === "high" ? 1 : 0),
        stepUp: prev.stepUp + (payload.step_up_required ? 1 : 0),
      }));
    }
    socket.on("login_scored", onLoginScored);
    return () => {
      socket.off("login_scored", onLoginScored);
    };
  }, []);

  return stats;
}
