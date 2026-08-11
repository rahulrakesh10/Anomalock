import type { LoginEventIn, ScoreOut } from "./types";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function scoreLogin(event: LoginEventIn): Promise<ScoreOut> {
  const res = await fetch(`${API_URL}/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event),
  });
  if (!res.ok) {
    throw new Error(`Score request failed: ${res.status} ${await res.text()}`);
  }
  return res.json();
}
