import type { LoginEventIn } from "./types";

/**
 * Each preset is two events: a "seed" baseline login sent quietly first
 * (so the model has a personal history to compare against — without it,
 * every login looks trivially "novel" and scenarios can't be
 * distinguished), then the actual scenario login the user sees scored.
 *
 * The seed is timestamped a day in the past for the "normal"/"new device"
 * scenarios (an ordinary established pattern). For "impossible travel" the
 * seed is only ~10 minutes before the attack login — that short gap
 * combined with a huge distance is exactly what makes the velocity
 * impossible.
 */

const BASELINE = {
  ip_address: "193.213.115.10",
  country: "NO",
  city: "Oslo",
  asn: 2116,
  browser: "Chrome 124.0.0.0",
  os: "Windows 10",
  device_type: "desktop",
};

const NEW_DEVICE = {
  ip_address: "185.107.56.20",
  country: "NO",
  city: "Oslo",
  asn: 39771,
  browser: "Safari 17.0",
  os: "iOS 17.4",
  device_type: "mobile",
};

const FAR_AWAY = {
  ip_address: "177.10.20.30",
  country: "BR",
  city: "Sao Paulo",
  asn: 28573,
  browser: "Chrome 124.0.0.0",
  os: "Windows 10",
  device_type: "desktop",
};

export type ScenarioKey = "normal" | "new_device" | "impossible_travel";

export const SCENARIOS: { key: ScenarioKey; label: string; description: string }[] = [
  { key: "normal", label: "Normal login", description: "Same device, network, and city the user always uses." },
  { key: "new_device", label: "New device", description: "Same city, but a device/network never seen before." },
  { key: "impossible_travel", label: "Impossible travel (attack)", description: "A login from another continent minutes after the last one." },
];

export function buildScenarioEvents(scenario: ScenarioKey, userId: string): { seed: LoginEventIn; actual: LoginEventIn } {
  const now = new Date();
  const seedTime = new Date(now.getTime() - 24 * 60 * 60 * 1000); // 1 day ago

  const seed: LoginEventIn = {
    user_id: userId,
    login_timestamp: seedTime.toISOString(),
    login_successful: true,
    ...BASELINE,
  };

  if (scenario === "normal") {
    return { seed, actual: { ...seed, user_id: userId, login_timestamp: now.toISOString() } };
  }

  if (scenario === "new_device") {
    return {
      seed,
      actual: { user_id: userId, login_timestamp: now.toISOString(), login_successful: true, ...NEW_DEVICE },
    };
  }

  // impossible_travel: seed only ~10 minutes before the attack login
  const recentSeedTime = new Date(now.getTime() - 10 * 60 * 1000);
  return {
    seed: { ...seed, login_timestamp: recentSeedTime.toISOString() },
    actual: { user_id: userId, login_timestamp: now.toISOString(), login_successful: true, ...FAR_AWAY },
  };
}
