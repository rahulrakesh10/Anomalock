"""Baseline: simple threshold rules on the engineered features.

This represents what many production systems still rely on today — static
if/else thresholds, no learning. It's the floor the ML models need to beat
to justify their added complexity. Thresholds below are set from the
feature-vs-label means observed in the EDA/feature-validation step (e.g.
mean hour_of_day_zscore was ~4.5 for confirmed ATO vs. ~0.3 otherwise), not
tuned against the test set.

Thresholds are named constants so the API (Phase 3) can reuse the exact
same rule definitions for its human-readable "flagged reasons" instead of
duplicating magic numbers.
"""

from __future__ import annotations

import pandas as pd

HOUR_ZSCORE_THRESHOLD = 3
USER_FAIL_COUNT_THRESHOLD = 5
IP_FAIL_COUNT_THRESHOLD = 10


def baseline_flag(df: pd.DataFrame) -> pd.Series:
    rules = (
        df["impossible_travel"]
        | (df["asn_novel"] & df["ip_novel"] & df["device_novel"])
        | (df["hour_of_day_zscore"] > HOUR_ZSCORE_THRESHOLD)
        | (df["user_fail_count_1h"] >= USER_FAIL_COUNT_THRESHOLD)
        | (df["ip_fail_count_24h"] >= IP_FAIL_COUNT_THRESHOLD)
    )
    return rules.fillna(False)


def baseline_reasons(f: dict) -> list[str]:
    """Same rules as baseline_flag, applied to a single event's feature
    dict, returning which specific rule(s) fired (for a human-readable
    explanation rather than just a yes/no flag)."""
    reasons = []
    if f.get("impossible_travel"):
        reasons.append("impossible_travel")
    if f.get("asn_novel") and f.get("ip_novel") and f.get("device_novel"):
        reasons.append("new_device_new_network")
    if f.get("hour_of_day_zscore", 0) > HOUR_ZSCORE_THRESHOLD:
        reasons.append("unusual_login_time")
    if f.get("user_fail_count_1h", 0) >= USER_FAIL_COUNT_THRESHOLD:
        reasons.append("high_user_failure_rate")
    if f.get("ip_fail_count_24h", 0) >= IP_FAIL_COUNT_THRESHOLD:
        reasons.append("high_ip_failure_rate")
    return reasons
