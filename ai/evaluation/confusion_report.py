# confusion_report.py
"""Generate a plain‑text confusion‑matrix report for DeepGuard AI.

This script reads the CSV produced by `evaluate.py` and writes a file
`confusion_report.txt` in `ai/evaluation/results/` containing:

- True Positive (TP)
- True Negative (TN)
- False Positive (FP)
- False Negative (FN)

Real images are labeled **0** and Fake images **1**.

Usage:
    python confusion_report.py
"""

import csv
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix

RESULTS_DIR = Path(__file__).parent / "results"
CSV_PATH = RESULTS_DIR / "evaluation_report.csv"
REPORT_PATH = RESULTS_DIR / "confusion_report.txt"

if not CSV_PATH.is_file():
    raise FileNotFoundError(f"Evaluation report not found at {CSV_PATH}")

labels = []
preds = []
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["predicted"] in ("", None):
            continue
        labels.append(int(row["ground_truth"]))
        preds.append(int(row["predicted"]))

labels = np.array(labels)
preds = np.array(preds)

# Compute confusion matrix: rows = true, cols = pred
cm = confusion_matrix(labels, preds, labels=[0, 1])
TN, FP, FN, TP = cm.ravel()

report = (
    "Confusion Matrix Report (Real=0, Fake=1)\n"
    "---------------------------------------\n"
    f"True Positive  (TP): {TP}\n"
    f"True Negative  (TN): {TN}\n"
    f"False Positive (FP): {FP}\n"
    f"False Negative (FN): {FN}\n"
    "\nFull matrix (rows = true, cols = pred):\n"
    f"[[{TN} {FP}]\n [{FN} {TP}]]\n"
)

REPORT_PATH.write_text(report, encoding="utf-8")
print(f"Confusion matrix saved to {REPORT_PATH}")
