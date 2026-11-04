# threshold_analysis.py
"""Analyze classification thresholds for the DeepGuard AI model.

The model outputs a probability for the *Fake* class (class 1).  The default
threshold is 0.5 (>= 0.5 → Fake, < 0.5 → Real).  This script evaluates a range of
thresholds and reports the resulting metrics.  It does **not** arbitrarily pick
a threshold; instead it records the performance of each threshold and highlights
the best one (based on F1‑score).

Outputs (saved in `ai/evaluation/results/`):
- `threshold_metrics.csv` – one row per threshold with accuracy, precision,
  recall and F1.
- `threshold_summary.txt` – human‑readable summary that includes:
    * metrics for the default 0.5 threshold
    * the best threshold (highest F1) and its metrics

Usage:
    python threshold_analysis.py
"""

import csv
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

RESULTS_DIR = Path(__file__).parent / "results"
CSV_PATH = RESULTS_DIR / "evaluation_report.csv"
THRESHOLD_CSV = RESULTS_DIR / "threshold_metrics.csv"
SUMMARY_TXT = RESULTS_DIR / "threshold_summary.txt"

if not CSV_PATH.is_file():
    raise FileNotFoundError(f"Evaluation report not found at {CSV_PATH}")

# Load ground‑truth labels and fake probabilities
labels = []
prob_fake = []
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Skip rows where inference failed
        if row["predicted"] in ("", None):
            continue
        labels.append(int(row["ground_truth"]))
        pf = row.get("prob_fake")
        prob_fake.append(float(pf) if pf not in ("", None) else np.nan)

labels = np.array(labels)
prob_fake = np.array(prob_fake, dtype=float)

# If there are no samples, we cannot perform analysis
if labels.size == 0:
    raise ValueError("No evaluation samples available for threshold analysis.")

# Define thresholds to evaluate – reasonable granularity
thresholds = np.arange(0.0, 1.01, 0.01)  # 0.00, 0.01, …, 1.00

rows = []
best_f1 = -1.0
best_thr = None
best_metrics = None

for thr in thresholds:
    preds = (prob_fake >= thr).astype(int)
    acc = accuracy_score(labels, preds)
    prec = precision_score(labels, preds, zero_division=0)
    rec = recall_score(labels, preds, zero_division=0)
    f1 = f1_score(labels, preds, zero_division=0)
    rows.append({
        "threshold": f"{thr:.2f}",
        "accuracy": f"{acc:.4f}",
        "precision": f"{prec:.4f}",
        "recall": f"{rec:.4f}",
        "f1": f"{f1:.4f}"
    })
    if f1 > best_f1:
        best_f1 = f1
        best_thr = thr
        best_metrics = (acc, prec, rec, f1)

# Write the full CSV
fieldnames = ["threshold", "accuracy", "precision", "recall", "f1"]
with open(THRESHOLD_CSV, "w", newline="", encoding="utf-8") as cf:
    writer = csv.DictWriter(cf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# Default‑threshold metrics (0.5)
def default_row_for(threshold):
    for r in rows:
        if abs(float(r["threshold"]) - threshold) < 1e-9:
            return r
    return None

default_row = default_row_for(0.5)

# Summary text
summary = (
    "Threshold Analysis Summary\n"
    "===========================\n"
    f"Dataset size: {labels.size} samples\n\n"
    "Default threshold (0.5):\n"
    f"  Accuracy : {default_row['accuracy']}\n"
    f"  Precision: {default_row['precision']}\n"
    f"  Recall   : {default_row['recall']}\n"
    f"  F1‑score : {default_row['f1']}\n\n"
    "Best threshold (highest F1‑score):\n"
    f"  Threshold: {best_thr:.2f}\n"
    f"  Accuracy : {best_metrics[0]:.4f}\n"
    f"  Precision: {best_metrics[1]:.4f}\n"
    f"  Recall   : {best_metrics[2]:.4f}\n"
    f"  F1‑score : {best_metrics[3]:.4f}\n"
)

SUMMARY_TXT.write_text(summary, encoding="utf-8")

print(f"Threshold CSV saved to {THRESHOLD_CSV}")
print(f"Summary report saved to {SUMMARY_TXT}")
