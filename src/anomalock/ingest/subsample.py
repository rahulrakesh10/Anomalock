"""Subsample the raw RBA login dataset down to a size usable for local dev.

The full RBA dataset (Wiefling et al., "Login Data Set for Risk-Based
Authentication") has 33M+ login events. We keep a stratified, *user-level*
subsample of ~300K rows so that:
  - All rows with the rare ground-truth label `Is Account Takeover` are
    kept (only ~140 of 33M+ rows across the full dataset — losing them to
    random sampling would remove the only confirmed-attack ground truth we
    have). Note `Is Attack IP` is a much noisier IP-reputation heuristic
    (true for ~9% of all logins, mostly false positives per the dataset's
    own paper) — it is NOT used to decide which users to force-keep, only
    kept as a regular feature/signal that appears naturally in the sample.
  - Users are sampled *whole* (every event belonging to a sampled user is
    kept), not individual rows in isolation. Per-user behavioral features
    (login velocity, time-of-day deviation, device/IP novelty) need a
    user's full event history to be computed correctly — sampling
    individual rows would silently corrupt those features with gaps.

This runs in two passes over the raw CSV (it does not fit in memory):
  1. Stream User ID + attack-label columns only, to decide which users to
     keep (all attacker users, plus a random sample of benign users large
     enough to hit --target-rows).
  2. Stream the full CSV again, keeping only rows for chosen users.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"

ATTACK_COLS = ["Is Attack IP", "Is Account Takeover"]
# Only this column is rare, confirmed ground truth; it decides forced keeps.
GROUND_TRUTH_COL = "Is Account Takeover"
ID_COLS = ["User ID"] + ATTACK_COLS


def _select_users(src_csv: Path, target_rows: int, seed: int, chunksize: int) -> set[str]:
    user_event_counts: dict[str, int] = {}
    ato_users: set[str] = set()

    reader = pd.read_csv(src_csv, usecols=lambda c: c in ID_COLS, chunksize=chunksize, low_memory=False)
    for chunk in reader:
        counts = chunk["User ID"].value_counts()
        for uid, n in counts.items():
            user_event_counts[uid] = user_event_counts.get(uid, 0) + int(n)

        if GROUND_TRUTH_COL in chunk.columns:
            is_ato = chunk[GROUND_TRUTH_COL] == True  # noqa: E712
            ato_users.update(chunk.loc[is_ato, "User ID"].unique())

    kept = set(ato_users)
    kept_rows = sum(user_event_counts.get(u, 0) for u in kept)

    benign_users = [u for u in user_event_counts if u not in kept]
    rng = np.random.default_rng(seed)
    rng.shuffle(benign_users)

    for uid in benign_users:
        if kept_rows >= target_rows:
            break
        kept.add(uid)
        kept_rows += user_event_counts[uid]

    print(f"Selected {len(kept):,} users ({len(ato_users):,} with confirmed account takeover), ~{kept_rows:,} rows")
    return kept


def subsample(src_csv: Path, target_rows: int = 300_000, seed: int = 42, chunksize: int = 500_000) -> pd.DataFrame:
    keep_users = _select_users(src_csv, target_rows, seed, chunksize)

    kept_chunks: list[pd.DataFrame] = []
    reader = pd.read_csv(src_csv, chunksize=chunksize, low_memory=False)
    for chunk in reader:
        kept_chunks.append(chunk[chunk["User ID"].isin(keep_users)])

    df = pd.concat(kept_chunks, ignore_index=True)
    return df.sort_values(["User ID", "Login Timestamp"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=RAW_DIR / "rba-dataset.csv")
    parser.add_argument("--out", type=Path, default=PROCESSED_DIR / "rba_sample.parquet")
    parser.add_argument("--target-rows", type=int, default=300_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = subsample(args.src, target_rows=args.target_rows, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)

    print(f"Wrote {len(df):,} rows / {df['User ID'].nunique():,} users to {args.out}")
    for col in ATTACK_COLS:
        if col in df.columns:
            print(f"  {col} = True: {int((df[col] == True).sum()):,}")  # noqa: E712


if __name__ == "__main__":
    main()
