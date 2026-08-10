"""Shared evaluation: precision, recall, false-positive rate.

Accuracy is not reported as a headline metric — with ~0.05% positive rate,
"flag nothing" scores 99.95% accuracy while catching zero attacks. Recall
(did we catch the attack) and false-positive rate (how often did we
wrongly flag/step-up a legitimate user) are what actually matter for a
risk-based auth system, since false positives have a real cost (annoyed,
locked-out users).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix


def recall_at_k(y_true: pd.Series, scores: pd.Series, k: float) -> dict:
    """Recall when only the top-`k` fraction of riskiest logins (by score,
    higher = riskier) are flagged.

    Rule-based baselines can't be tuned to a review budget — they either
    fire on a rule or they don't. Score-based models (Isolation Forest,
    Random Forest) can be ranked and cut off at whatever budget a review
    team can actually handle (e.g. "we can only step-up-auth 1% of
    logins"), which is how these models would actually be operated in
    production. This also sidesteps the classifier's raw probability
    threshold, which is poorly calibrated under class_weight='balanced'.

    Tie-breaking: with a mostly boolean/low-cardinality feature set, many
    rows land on the exact same score (e.g. Random Forest's predict_proba
    collapses tens of thousands of test rows onto a handful of discrete
    values here) — the model genuinely cannot distinguish within a tied
    group. Taking `scores >= threshold` would include the *entire* tied
    group and blow past the budget by orders of magnitude. Instead we break
    ties with a fixed random draw (seeded, so results are reproducible),
    which is the standard, honest way to pick an exact-size top-k when a
    model's output resolution is coarser than the requested budget — it's
    equivalent to what a review team would have to do anyway (pick some of
    the equally-scored logins, since the model gives no further basis to
    prefer one over another).
    """
    n_flag = max(1, int(len(scores) * k))
    tiebreak = pd.Series(np.random.default_rng(0).random(len(scores)), index=scores.index)
    order = pd.DataFrame({"score": scores, "tiebreak": tiebreak}).sort_values(
        ["score", "tiebreak"], ascending=False
    )
    flagged = pd.Series(False, index=scores.index)
    flagged.loc[order.index[:n_flag]] = True
    tp = int((flagged & y_true).sum())
    recall = tp / y_true.sum() if y_true.sum() else 0.0
    precision = tp / flagged.sum() if flagged.sum() else 0.0
    return {"k": k, "n_flagged": int(flagged.sum()), "true_positives": tp, "recall": recall, "precision": precision}


def evaluate(y_true: pd.Series, y_pred: pd.Series) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[False, True]).ravel()
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "false_positive_rate": fpr,
        "true_positives": int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_negatives": int(tn),
        "flagged_count": int(tp + fp),
    }
