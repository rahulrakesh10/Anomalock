"""Baseline: simple threshold rules on the engineered features.

This represents what many production systems still rely on today — static
if/else thresholds, no learning. It's the floor the ML models need to beat
to justify their added complexity. Thresholds below are set from the
feature-vs-label means observed in the EDA/feature-validation step (e.g.
mean hour_of_day_zscore was ~4.5 for confirmed ATO vs. ~0.3 otherwise), not
tuned against the test set.
"""

from __future__ import annotations

import pandas as pd


def baseline_flag(df: pd.DataFrame) -> pd.Series:
    rules = (
        df["impossible_travel"]
        | (df["asn_novel"] & df["ip_novel"] & df["device_novel"])
        | (df["hour_of_day_zscore"] > 3)
        | (df["user_fail_count_1h"] >= 5)
        | (df["ip_fail_count_24h"] >= 10)
    )
    return rules.fillna(False)
