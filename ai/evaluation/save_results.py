# save_results.py
"""Generate final evaluation JSON and CSV files.

- Reads `ai/evaluation/results/evaluation_report.csv` produced by `evaluate.py`.
- Computes dataset statistics (real/fake sample counts, total).
- Calculates metrics (accuracy, precision, recall, f1, roc_auc) using the same
  logic as `metrics.py`. If there are no samples or only one class, numeric
  metrics are set to 0 and ROC‑AUC is set to null.
- Writes:
    * `ai/evaluation/results/evaluation.json`
    * `ai/evaluation/results/per_image_results.csv`

Usage:
    python save_results.py
"""

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

RESULTS_DIR = Path(__file__).parent / "results"
REPORT_CSV = RESULTS_DIR / "evaluation_report.csv"
JSON_OUT = RESULTS_DIR / "evaluation.json"
PER_IMAGE_CSV = RESULTS_DIR / "per_image_results.csv"

# ---------------------------------------------------------------------------
# Load evaluation rows (may be empty)
# ---------------------------------------------------------------------------
rows = []
if REPORT_CSV.is_file():
    with open(REPORT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
else:
    raise FileNotFoundError(f"Evaluation report not found at {REPORT_CSV}")

# ---------------------------------------------------------------------------
# Dataset statistics
# ---------------------------------------------------------------------------
real_samples = sum(1 for r in rows if r.get("ground_truth") == "0")
fake_samples = sum(1 for r in rows if r.get("ground_truth") == "1")
total_samples = len(rows)

# ---------------------------------------------------------------------------
# Metric computation (guard against empty data)
# ---------------------------------------------------------------------------
if total_samples == 0:
    metrics = {
        "accuracy": 0,
        "precision": 0,
        "recall": 0,
        "f1": 0,
        "roc_auc": None,
    }
else:
    labels = np.array([int(r["ground_truth"]) for r in rows])
    preds = np.array([int(r["predicted"]) for r in rows])
    # probabilities – use prob_fake if present, else fallback to 0.0
    prob_fake_vals = []
    for r in rows:
        pf = r.get("prob_fake")
        prob_fake_vals.append(float(pf) if pf not in ("", None) else np.nan)
    prob_fake = np.array(prob_fake_vals, dtype=float)

    accuracy = accuracy_score(labels, preds)
    precision = precision_score(labels, preds, zero_division=0)
    recall = recall_score(labels, preds, zero_division=0)
    f1 = f1_score(labels, preds, zero_division=0)
    # ROC‑AUC only if both classes present and we have valid probabilities
    if len(np.unique(labels)) == 2 and not np.isnan(prob_fake).all():
        roc_auc = roc_auc_score(labels, prob_fake)
    else:
        roc_auc = None

    metrics = {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
    }

# ---------------------------------------------------------------------------
# Write JSON summary
# ---------------------------------------------------------------------------
summary = {
    "model": "EfficientNet-B0 FF++ C23",
    "dataset": {
        "real_samples": real_samples,
        "fake_samples": fake_samples,
        "total_samples": total_samples,
    },
    "metrics": metrics,
}
with open(JSON_OUT, "w", encoding="utf-8") as jf:
    json.dump(summary, jf, indent=2)

# ---------------------------------------------------------------------------
# Write per‑image CSV (header only if no rows)
# ---------------------------------------------------------------------------
fieldnames = [
    "filename",
    "ground_truth",
    "prediction",
    "real_probability",
    "fake_probability",
    "correct",
]
with open(PER_IMAGE_CSV, "w", newline="", encoding="utf-8") as cf:
    writer = csv.DictWriter(cf, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow({
            "filename": r.get("filename"),
            "ground_truth": r.get("ground_truth"),
            "prediction": r.get("predicted"),
            "real_probability": r.get("prob_real"),
            "fake_probability": r.get("prob_fake"),
            "correct": r.get("correct"),
        })

print(f"JSON summary saved to {JSON_OUT}")
print(f"Per‑image CSV saved to {PER_IMAGE_CSV}")
