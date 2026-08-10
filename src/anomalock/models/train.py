"""Train baseline / Isolation Forest / Random Forest and compare them.

Usage:
    python -m anomalock.models.train
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.inspection import permutation_importance

from anomalock.features.build_features import FEATURE_COLUMNS
from anomalock.models.baseline import baseline_flag
from anomalock.models.evaluate import evaluate, recall_at_k
from anomalock.models.split import chronological_split

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"
FEATURES_PATH = Path(__file__).resolve().parents[3] / "data" / "processed" / "rba_features.parquet"

LABEL_COL = "Is Account Takeover"
# IsolationForest's contamination and the RF class weighting both need a
# rough prior on attack prevalence. We use the *train-set* empirical rate
# rather than a round number, so it reflects what's actually in this data.
RANDOM_STATE = 42


def prepare_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    df = df.copy()
    # A user's first-ever login has no prior point to compute velocity
    # from (see build_features.add_login_velocity). Rather than silently
    # imputing a value that looks like "normal", we make the missingness
    # itself a feature and zero-fill the rest so sklearn can consume it.
    df["is_first_login"] = df["login_velocity_kmh"].isna()
    df["login_velocity_kmh"] = df["login_velocity_kmh"].fillna(0.0)

    feature_cols = FEATURE_COLUMNS + ["is_first_login"]
    X = df[feature_cols].astype(float)
    y = df[LABEL_COL].astype(bool)
    return X, y


def run() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    df = pd.read_parquet(FEATURES_PATH)

    train_df, test_df = chronological_split(df)
    X_train, y_train = prepare_xy(train_df)
    X_test, y_test = prepare_xy(test_df)

    print(f"Train: {len(train_df):,} rows, {y_train.sum()} positives")
    print(f"Test:  {len(test_df):,} rows, {y_test.sum()} positives")

    results = {}

    # --- Baseline ---
    baseline_pred = baseline_flag(test_df)
    results["baseline"] = evaluate(y_test, baseline_pred)

    # --- Isolation Forest (unsupervised) ---
    # Trained without labels, as it would be in production where confirmed
    # ATO labels are rarely available at training time. `contamination` is
    # set from the train-set empirical attack rate as a rough prior on how
    # much of the traffic to flag as anomalous.
    train_contamination = max(y_train.mean(), 1e-4)
    iso = IsolationForest(
        n_estimators=200,
        contamination=train_contamination,
        random_state=RANDOM_STATE,
    )
    iso.fit(X_train)
    iso_pred = pd.Series(iso.predict(X_test) == -1, index=X_test.index)
    results["isolation_forest"] = evaluate(y_test, iso_pred)
    # decision_function: lower = more anomalous, so negate for a "higher = riskier" score
    iso_scores = pd.Series(-iso.decision_function(X_test), index=X_test.index)

    # --- Random Forest (supervised) ---
    rf = RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    rf_pred = pd.Series(rf.predict(X_test), index=X_test.index)
    results["random_forest"] = evaluate(y_test, rf_pred)
    rf_scores = pd.Series(rf.predict_proba(X_test)[:, 1], index=X_test.index)

    # --- Recall at a fixed review budget (score-based models only) ---
    budget_results = {}
    for k in (0.005, 0.01, 0.02, 0.05, 0.20):
        budget_results[f"isolation_forest@{k}"] = recall_at_k(y_test, iso_scores, k)
        budget_results[f"random_forest@{k}"] = recall_at_k(y_test, rf_scores, k)
    budget_df = pd.DataFrame(budget_results).T
    budget_df.to_csv(REPORTS_DIR / "recall_at_budget.csv")

    # --- Permutation importance (Random Forest) ---
    # average_precision is used instead of the default accuracy score,
    # since accuracy is meaningless at this class imbalance (see evaluate.py).
    perm = permutation_importance(
        rf, X_test, y_test, n_repeats=20, random_state=RANDOM_STATE, scoring="average_precision", n_jobs=-1
    )
    importance = (
        pd.DataFrame({"feature": X_test.columns, "importance_mean": perm.importances_mean, "importance_std": perm.importances_std})
        .sort_values("importance_mean", ascending=False)
    )
    importance.to_csv(REPORTS_DIR / "permutation_importance.csv", index=False)

    fig, ax = plt.subplots(figsize=(7, 5))
    order = importance.sort_values("importance_mean")
    ax.barh(order["feature"], order["importance_mean"], xerr=order["importance_std"])
    ax.set_xlabel("Permutation importance (drop in average precision)")
    ax.set_title("Random Forest feature importance")
    fig.tight_layout()
    fig.savefig(REPORTS_DIR / "permutation_importance.png", dpi=150)

    # --- Save comparison table ---
    comparison = pd.DataFrame(results).T
    comparison.to_csv(REPORTS_DIR / "model_comparison.csv")

    with open(REPORTS_DIR / "results.json", "w") as f:
        json.dump({"results": results, "n_train": len(train_df), "n_test": len(test_df),
                   "train_positives": int(y_train.sum()), "test_positives": int(y_test.sum())}, f, indent=2)

    print()
    print(comparison[["precision", "recall", "false_positive_rate", "true_positives", "false_positives"]])
    print()
    print("Recall at fixed review budget:")
    print(budget_df[["n_flagged", "true_positives", "recall", "precision"]])
    print()
    print("Top permutation-importance features:")
    print(importance.head(10).to_string(index=False))


if __name__ == "__main__":
    run()
