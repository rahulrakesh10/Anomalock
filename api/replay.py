"""Replay historical/test login events through the live /score endpoint,
to simulate real traffic hitting the API (and, in Phase 4, feed the
live dashboard).

Usage:
    python -m api.replay --limit 500 --delay 0.05
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import httpx
import pandas as pd

FEATURES_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "rba_features.parquet"


def event_payload(row: pd.Series) -> dict:
    return {
        "user_id": str(row["User ID"]),
        "login_timestamp": row["Login Timestamp"].isoformat(),
        "ip_address": row["IP Address"],
        "country": row["Country"] if pd.notna(row["Country"]) else None,
        "region": row["Region"] if pd.notna(row["Region"]) else None,
        "city": row["City"] if pd.notna(row["City"]) else None,
        "asn": int(row["ASN"]) if pd.notna(row["ASN"]) else None,
        "browser": row["Browser Name and Version"] if pd.notna(row["Browser Name and Version"]) else None,
        "os": row["OS Name and Version"] if pd.notna(row["OS Name and Version"]) else None,
        "device_type": row["Device Type"] if pd.notna(row["Device Type"]) else None,
        "login_successful": bool(row["Login Successful"]),
    }


def run(base_url: str, limit: int, delay: float, start: int) -> None:
    df = pd.read_parquet(FEATURES_PATH).sort_values("Login Timestamp").reset_index(drop=True)
    df = df.iloc[start : start + limit] if limit else df.iloc[start:]

    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        for i, row in df.iterrows():
            payload = event_payload(row)
            resp = client.post("/score", json=payload)
            resp.raise_for_status()
            result = resp.json()
            label = "ATO" if row["Is Account Takeover"] else "   "
            print(
                f"[{i}] {label} user={payload['user_id']:<22} risk={result['risk_score']:5.1f} "
                f"level={result['risk_level']:<6} step_up={result['step_up_required']} "
                f"reasons={result['flagged_reasons']}"
            )
            if delay:
                time.sleep(delay)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--limit", type=int, default=200, help="0 = replay all rows")
    parser.add_argument("--delay", type=float, default=0.05, help="seconds between requests")
    parser.add_argument("--start", type=int, default=0)
    args = parser.parse_args()
    run(args.base_url, args.limit, args.delay, args.start)
