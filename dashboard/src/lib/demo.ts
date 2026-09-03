import { scoreLogin } from "./api";
import { buildScenarioEvents, type ScenarioKey } from "./scenarios";

/**
 * A scripted mix of fictional logins, run once on load so the dashboard
 * isn't empty on first paint (a portfolio demo landed on cold is a much
 * worse first impression than a live feed already in motion). Every event
 * is scored through the real API — nothing here is faked client-side, it's
 * just a script of *which* logins to send and when.
 *
 * Usernames get a random per-run suffix (below) rather than being fixed:
 * the "new device" / "impossible travel" scenarios only look dramatic
 * against a user with an established baseline and *no* prior exposure to
 * the attack pattern itself. A fixed demo username would accumulate real
 * history in Postgres across every visitor and every "Replay demo" click,
 * and after enough runs the model would (correctly!) stop treating a
 * repeat "impossible travel" login from the same two cities as novel.
 * Randomizing guarantees each run starts from a genuinely fresh identity.
 */
const DEMO_SCRIPT: { user: string; scenario: ScenarioKey }[] = [
  { user: "alex.chen", scenario: "normal" },
  { user: "priya.nair", scenario: "new_device" },
  { user: "sofia.rossi", scenario: "normal" },
  { user: "marcus.webb", scenario: "impossible_travel" },
  { user: "daniel.kim", scenario: "new_device" },
];

const STEP_DELAY_MS = 1100;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function runId(): string {
  return Math.random().toString(36).slice(2, 8);
}

export async function runDemo(signal: { cancelled: boolean }): Promise<void> {
  const suffix = runId();
  for (const step of DEMO_SCRIPT) {
    if (signal.cancelled) return;
    const { seed, actual } = buildScenarioEvents(step.scenario, `${step.user}.${suffix}`);
    try {
      await scoreLogin(seed);
      await sleep(220);
      if (signal.cancelled) return;
      await scoreLogin(actual);
    } catch {
      // API may still be cold-starting on first load — skip this step
      // rather than blocking the rest of the script.
    }
    await sleep(STEP_DELAY_MS);
  }
}
