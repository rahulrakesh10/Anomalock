"""Chronological train/test split.

We split by time, not randomly across rows, so evaluation mirrors how the
system would actually be used: build behavioral history from the past,
score logins that happen after that point. A random row-level split would
leak future information (a user's later events would help predict their
earlier ones via the causal features) and overstate performance.

Cutoff choice: all 141 confirmed `Is Account Takeover` events in this
subsample happen to fall between Feb-Nov 2020 (the full RBA dataset's
labeled attack waves are concentrated early in the collection window) —
none in Dec 2020-Feb 2021. A "last few months as test" split would put
zero positive labels in the test set, making precision/recall undefined.
We use 2020-09-01 as the cutoff, which keeps a workable number of ATO
events on both sides (~103 train / ~38 test) while still holding out the
most recent ~5 months as test. This is a direct consequence of how sparse
and clustered the ground-truth label is here — not a choice made to
flatter the numbers — and is called out in reports/model_comparison.md.
"""

from __future__ import annotations

import pandas as pd

TRAIN_CUTOFF = pd.Timestamp("2020-09-01")


def chronological_split(df: pd.DataFrame, cutoff: pd.Timestamp = TRAIN_CUTOFF) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df["Login Timestamp"] < cutoff].copy()
    test = df[df["Login Timestamp"] >= cutoff].copy()
    return train, test
