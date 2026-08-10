"""Fit the Isolation Forest that the API actually serves.

Phase 2's train.py fits on the chronological *train* split only, so its
reported metrics are a fair held-out evaluation. For serving, that
train/test distinction doesn't apply — a real deployment trains on all
history available up to "now" — so this script fits on the full feature
set and saves the artifact the API loads at startup.

Usage:
    python -m anomalock.models.train_serving_model
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from anomalock.models.train import prepare_xy

ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "artifacts"
FEATURES_PATH = Path(__file__).resolve().parents[3] / "data" / "processed" / "rba_features.parquet"
RANDOM_STATE = 42


def run() -> None:
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    df = pd.read_parquet(FEATURES_PATH)
    X, y = prepare_xy(df)

    contamination = max(y.mean(), 1e-4)
    model = IsolationForest(n_estimators=200, contamination=contamination, random_state=RANDOM_STATE)
    model.fit(X)

    joblib.dump(model, ARTIFACTS_DIR / "isolation_forest.joblib")

    # Raw Isolation Forest scores are not meaningful on their own (unbounded,
    # no fixed scale). We store the training score distribution as 101
    # percentile anchors so the API can map a new raw score to an
    # interpretable "riskier than N% of known history" 0-100 value via
    # linear interpolation, rather than exposing the raw score directly.
    raw_scores = -model.decision_function(X)  # higher = more anomalous
    percentiles = np.percentile(raw_scores, np.arange(101)).tolist()

    with open(ARTIFACTS_DIR / "model_meta.json", "w") as f:
        json.dump(
            {
                "feature_columns": list(X.columns),
                "contamination": contamination,
                "n_train_rows": len(X),
                "score_percentiles": percentiles,
            },
            f,
            indent=2,
        )

    print(f"Saved model trained on {len(X):,} rows to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    run()
