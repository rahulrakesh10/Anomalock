"""Behavioral feature engineering for login-risk scoring.

All features are computed **causally**: for a given login event, only that
user's (or IP's) *strictly prior* events are used. This matters for two
reasons — it's how a real risk-scoring system actually works (you can only
use history you've already observed), and computing features from future
events would leak label-correlated information into training and inflate
offline metrics in a way that won't hold up in production.

The dataframe must be pre-sorted is handled internally; pass the raw
(deduplicated) login events dataframe as loaded from
`data/processed/rba_sample.parquet`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from anomalock.features.geo import resolve_coords

EARTH_RADIUS_KM = 6371.0
# Fastest scheduled commercial flights cruise around 900-950 km/h. A login
# velocity above this implies the same user couldn't physically have
# traveled between the two locations in the time between logins.
IMPOSSIBLE_TRAVEL_KMH = 900.0

USER_FAIL_WINDOW = "1h"   # per-user failed-login rolling window: catches fast/bursty brute force
IP_FAIL_WINDOW = "24h"    # per-IP failed-login rolling window: catches slow/low brute force spread over a day


def _haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a.clip(0, 1)))


def add_geo_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Resolve (City, Country) -> (lat, lon) once per unique pair (cheap — a
    few thousand unique pairs vs. hundreds of thousands of rows)."""
    pairs = df[["City", "Country"]].drop_duplicates()
    pairs["_coords"] = pairs.apply(lambda r: resolve_coords(r["City"], r["Country"]), axis=1)
    pairs["lat"] = pairs["_coords"].apply(lambda c: c[0] if c else np.nan)
    pairs["lon"] = pairs["_coords"].apply(lambda c: c[1] if c else np.nan)
    return df.merge(pairs[["City", "Country", "lat", "lon"]], on=["City", "Country"], how="left")


def add_login_velocity(df: pd.DataFrame) -> pd.DataFrame:
    """Feature 1 — implied travel speed between a user's consecutive logins.

    Rationale: a legitimate user cannot physically log in from Oslo and then
    from São Paulo 20 minutes later. A velocity that exceeds commercial
    flight speed is strong, hard-to-fake evidence of a compromised account
    being used from a second location (or a shared/leaked credential).
    """
    g = df.sort_values(["User ID", "Login Timestamp"]).groupby("User ID")
    prev_lat, prev_lon = g["lat"].shift(1), g["lon"].shift(1)
    prev_ts = g["Login Timestamp"].shift(1)

    dist_km = _haversine_km(df["lat"], df["lon"], prev_lat, prev_lon)
    hours = (df["Login Timestamp"] - prev_ts).dt.total_seconds() / 3600.0
    # Sub-minute gaps would produce absurd speeds from GPS/geocoding noise
    # alone; floor the elapsed time at 1 minute so velocity stays meaningful.
    hours_floored = hours.clip(lower=1 / 60)

    velocity = dist_km / hours_floored
    velocity = velocity.where(prev_ts.notna())  # NaN for each user's first login — no prior point to compare

    df["login_velocity_kmh"] = velocity
    df["impossible_travel"] = velocity > IMPOSSIBLE_TRAVEL_KMH
    df["impossible_travel"] = df["impossible_travel"].fillna(False)
    return df


def add_failed_attempt_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Feature 2 — rolling failed-login counts, per user and per source IP.

    Rationale: a burst of failures for one user (short window) or from one
    IP across many accounts (longer window) is the classic brute-force /
    credential-stuffing signature. Splitting into a short per-user window
    and a longer per-IP window lets us catch both a fast attack against one
    account and a slow, low-and-slow attack spread across many accounts
    from a single source, which per-account rate limiting alone would miss.
    """
    df = df.sort_values(["User ID", "Login Timestamp"]).reset_index(drop=True)
    df["_is_failed"] = ~df["Login Successful"]
    df["_row_id"] = df.index

    def rolling_count(group_col: str, window: str) -> pd.Series:
        tmp = df[[group_col, "Login Timestamp", "_is_failed", "_row_id"]].sort_values([group_col, "Login Timestamp"])
        tmp["_count"] = (
            tmp.groupby(group_col)
            .apply(lambda g: g.set_index("Login Timestamp")["_is_failed"].rolling(window, closed="left").sum())
            .reset_index(level=0, drop=True)
            .values
        )
        return tmp.set_index("_row_id")["_count"].reindex(df["_row_id"]).values

    df["user_fail_count_1h"] = rolling_count("User ID", USER_FAIL_WINDOW)
    df["ip_fail_count_24h"] = rolling_count("IP Address", IP_FAIL_WINDOW)
    df[["user_fail_count_1h", "ip_fail_count_24h"]] = df[["user_fail_count_1h", "ip_fail_count_24h"]].fillna(0)

    df = df.drop(columns=["_is_failed", "_row_id"])
    return df


def add_time_of_day_deviation(df: pd.DataFrame) -> pd.DataFrame:
    """Feature 3 — how unusual this login's time-of-day/day-of-week is for
    this specific user, vs. their own history (not the global population).

    Rationale: a login at 3am is unremarkable for a night-shift worker and
    highly unusual for a 9-to-5 user. Personalizing "normal hours" per user,
    rather than using one global threshold, is what lets this catch
    off-hours anomalies without constant false positives across a diverse
    user base in different time zones/shifts.

    Circular handling: hour-of-day wraps around midnight (23:00 and 00:30
    are close, not far apart). We take the shortest signed distance around
    the 24h clock rather than a naive linear difference.
    """
    df = df.sort_values(["User ID", "Login Timestamp"]).reset_index(drop=True)
    hour = df["Login Timestamp"].dt.hour + df["Login Timestamp"].dt.minute / 60.0
    df["_hour"] = hour

    g = df.groupby("User ID")["_hour"]
    # expanding mean/std computed on *prior* logins only: shift(1) before expanding
    prior_hour = g.shift(1)
    hist_mean = prior_hour.groupby(df["User ID"]).expanding().mean().reset_index(level=0, drop=True)
    hist_std = prior_hour.groupby(df["User ID"]).expanding().std().reset_index(level=0, drop=True)

    raw_diff = df["_hour"] - hist_mean
    circular_diff = (raw_diff + 12) % 24 - 12  # shortest signed distance on a 24h clock
    z = circular_diff / hist_std.replace(0, np.nan)

    df["hour_of_day_zscore"] = z
    # New users (<2 prior logins, or zero historical variance) have no
    # meaningful personal baseline yet — default to 0 (neutral) rather than
    # NaN, since "unknown" should not itself be treated as risky.
    df["hour_of_day_zscore"] = df["hour_of_day_zscore"].fillna(0.0)

    # Day-of-week deviation: how rare this weekday is in the user's prior history.
    dow = df["Login Timestamp"].dt.dayofweek
    df["_dow"] = dow
    prior_dow = df.groupby("User ID")["_dow"].shift(1)
    same_dow_count = (
        df.assign(_same=prior_dow == df["_dow"])
        .groupby("User ID")["_same"]
        .expanding()
        .sum()
        .reset_index(level=0, drop=True)
    )
    prior_login_count = df.groupby("User ID").cumcount()  # number of prior logins for this user
    dow_freq = (same_dow_count / prior_login_count.replace(0, np.nan)).fillna(0.0)
    df["dow_deviation"] = 1.0 - dow_freq  # 1 = never seen this weekday before, 0 = always this weekday

    df = df.drop(columns=["_hour", "_dow"])
    return df


def add_novelty_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Feature 4 — has this user ever used this device / IP / ASN before?

    Rationale: attackers logging in with stolen credentials almost always
    do so from a device fingerprint, IP, and/or network (ASN) the real user
    has never used. This is one of the strongest and cheapest signals for
    a first login from a new device/network — the "new device at an odd
    hour" scenario called out in the problem statement.
    """
    df = df.sort_values(["User ID", "Login Timestamp"]).reset_index(drop=True)
    df["_device_sig"] = df["Browser Name and Version"].astype(str) + "|" + df["OS Name and Version"].astype(str)

    for col, out in [("_device_sig", "device_novel"), ("IP Address", "ip_novel"), ("ASN", "asn_novel")]:
        # cumcount()==0 within (User ID, value) means "first time this user
        # has ever produced this value" in chronological order == novel now.
        first_occurrence = df.groupby(["User ID", col]).cumcount() == 0
        df[out] = first_occurrence

    df = df.drop(columns=["_device_sig"])
    return df


def add_fail_success_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """Feature 5 — ratio of failed to successful attempts in a recent
    per-user window.

    Rationale: distinct from the raw failure *count* (Feature 2), the ratio
    captures attempts that look like brute force relative to how much this
    user normally logs in at all — a user with 1 failure out of 1 attempt
    looks very different from a user with 1 failure out of 50, even if the
    raw count is the same.
    """
    df = df.sort_values(["User ID", "Login Timestamp"]).reset_index(drop=True)
    df["_is_success"] = df["Login Successful"]
    df["_row_id"] = df.index

    tmp = df[["User ID", "Login Timestamp", "_is_success", "_row_id"]].sort_values(["User ID", "Login Timestamp"])
    tmp["_success_count"] = (
        tmp.groupby("User ID")
        .apply(lambda g: g.set_index("Login Timestamp")["_is_success"].rolling(USER_FAIL_WINDOW, closed="left").sum())
        .reset_index(level=0, drop=True)
        .values
    )
    success_count = tmp.set_index("_row_id")["_success_count"].reindex(df["_row_id"]).fillna(0).values

    df["fail_to_success_ratio_1h"] = df["user_fail_count_1h"] / (success_count + 1.0)
    df = df.drop(columns=["_is_success", "_row_id"])
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Login Timestamp"] = pd.to_datetime(df["Login Timestamp"])
    df = add_geo_columns(df)
    df = add_login_velocity(df)
    df = add_failed_attempt_rates(df)
    df = add_fail_success_ratio(df)
    df = add_time_of_day_deviation(df)
    df = add_novelty_flags(df)
    return df


FEATURE_COLUMNS = [
    "login_velocity_kmh",
    "impossible_travel",
    "user_fail_count_1h",
    "ip_fail_count_24h",
    "fail_to_success_ratio_1h",
    "hour_of_day_zscore",
    "dow_deviation",
    "device_novel",
    "ip_novel",
    "asn_novel",
]
