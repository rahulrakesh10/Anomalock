"""Online scoring: compute the same causal features as
anomalock.features.build_features, but from a single user's DB history
instead of a batch dataframe, then score with the saved Isolation Forest
and baseline rules.

Feature *definitions* here must stay consistent with build_features.py —
see that module for the full rationale behind each one. This module only
differs in *how* they're computed (per-request DB queries over one user's
history, vs. vectorized pandas over the whole dataset in training).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from anomalock.features.build_features import IMPOSSIBLE_TRAVEL_KMH, _haversine_km
from anomalock.features.geo import resolve_coords
from anomalock.models.baseline import baseline_reasons
from api.app.models import LoginEvent
from api.app.schemas import LoginEventIn

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"

USER_FAIL_WINDOW = dt.timedelta(hours=1)
IP_FAIL_WINDOW = dt.timedelta(hours=24)

HIGH_RISK_PERCENTILE = 90
MEDIUM_RISK_PERCENTILE = 70


class Scorer:
    def __init__(self) -> None:
        self.model = joblib.load(ARTIFACTS_DIR / "isolation_forest.joblib")
        with open(ARTIFACTS_DIR / "model_meta.json") as f:
            meta = json.load(f)
        self.feature_columns: list[str] = meta["feature_columns"]
        self.score_percentiles: list[float] = meta["score_percentiles"]

    def _normalize_score(self, raw_score: float) -> float:
        """Map a raw Isolation Forest score to a 0-100 value via the
        training score distribution's percentiles (see
        train_serving_model.py) — "riskier than N% of known history"."""
        return float(np.interp(raw_score, self.score_percentiles, np.arange(101)))

    def score(self, db: Session, event: LoginEventIn) -> tuple[dict, dict]:
        """Returns (features, score_info) — does not persist anything."""
        prior = (
            db.execute(
                select(LoginEvent)
                .where(LoginEvent.user_id == event.user_id, LoginEvent.login_timestamp < event.login_timestamp)
                .order_by(LoginEvent.login_timestamp.asc())
            )
            .scalars()
            .all()
        )

        features = self._compute_features(event, prior, db)

        x = pd.DataFrame([{c: features[c] for c in self.feature_columns}])
        raw_score = float(-self.model.decision_function(x)[0])
        risk_score = self._normalize_score(raw_score)

        reasons = baseline_reasons(features)
        if risk_score >= HIGH_RISK_PERCENTILE:
            level = "high"
        elif risk_score >= MEDIUM_RISK_PERCENTILE:
            level = "medium"
        else:
            level = "low"
        step_up_required = level == "high" or bool(reasons)

        score_info = {
            "risk_score": risk_score,
            "risk_level": level,
            "step_up_required": step_up_required,
            "flagged_reasons": reasons,
        }
        return features, score_info

    def _compute_features(self, event: LoginEventIn, prior: list[LoginEvent], db: Session) -> dict:
        f: dict = {}

        # --- login velocity / impossible travel ---
        if prior:
            last = prior[-1]
            cur_coords = resolve_coords(event.city, event.country)
            prev_coords = resolve_coords(last.city, last.country)
            hours = max((event.login_timestamp - last.login_timestamp).total_seconds() / 3600.0, 1 / 60)
            if cur_coords and prev_coords:
                dist_km = _haversine_km(cur_coords[0], cur_coords[1], prev_coords[0], prev_coords[1])
                velocity = dist_km / hours
            else:
                velocity = 0.0
            f["login_velocity_kmh"] = velocity
            f["impossible_travel"] = velocity > IMPOSSIBLE_TRAVEL_KMH
            f["is_first_login"] = 0.0
        else:
            f["login_velocity_kmh"] = 0.0
            f["impossible_travel"] = False
            f["is_first_login"] = 1.0

        # --- failed-attempt rates (per-user, 1h) ---
        user_window_start = event.login_timestamp - USER_FAIL_WINDOW
        recent_user = [e for e in prior if e.login_timestamp >= user_window_start]
        user_fail_count = sum(1 for e in recent_user if not e.login_successful)
        user_success_count = sum(1 for e in recent_user if e.login_successful)
        f["user_fail_count_1h"] = float(user_fail_count)
        f["fail_to_success_ratio_1h"] = user_fail_count / (user_success_count + 1.0)

        # --- failed-attempt rate (per-IP, 24h, across all users) ---
        ip_window_start = event.login_timestamp - IP_FAIL_WINDOW
        ip_fail_count = db.execute(
            select(func.count())
            .select_from(LoginEvent)
            .where(
                LoginEvent.ip_address == event.ip_address,
                LoginEvent.login_successful.is_(False),
                LoginEvent.login_timestamp >= ip_window_start,
                LoginEvent.login_timestamp < event.login_timestamp,
            )
        ).scalar_one()
        f["ip_fail_count_24h"] = float(ip_fail_count)

        # --- time-of-day / day-of-week deviation ---
        cur_hour = event.login_timestamp.hour + event.login_timestamp.minute / 60.0
        prior_hours = [e.login_timestamp.hour + e.login_timestamp.minute / 60.0 for e in prior]
        if len(prior_hours) == 0:
            f["hour_of_day_zscore"] = 0.0
        else:
            mean_hour = float(np.mean(prior_hours))
            raw_diff = cur_hour - mean_hour
            circular_diff = (raw_diff + 12) % 24 - 12
            std_hour = float(np.std(prior_hours, ddof=1)) if len(prior_hours) >= 2 else 0.0
            f["hour_of_day_zscore"] = circular_diff / std_hour if std_hour else 0.0

        cur_dow = event.login_timestamp.weekday()
        if len(prior) == 0:
            f["dow_deviation"] = 1.0
        else:
            same_dow = sum(1 for e in prior if e.login_timestamp.weekday() == cur_dow)
            f["dow_deviation"] = 1.0 - same_dow / len(prior)

        # --- novelty flags ---
        prior_devices = {f"{e.browser}|{e.os}" for e in prior}
        prior_ips = {e.ip_address for e in prior}
        prior_asns = {e.asn for e in prior}
        f["device_novel"] = f"{event.browser}|{event.os}" not in prior_devices
        f["ip_novel"] = event.ip_address not in prior_ips
        f["asn_novel"] = event.asn not in prior_asns

        return f


_scorer: Scorer | None = None


def get_scorer() -> Scorer:
    global _scorer
    if _scorer is None:
        _scorer = Scorer()
    return _scorer
