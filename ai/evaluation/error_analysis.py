# error_analysis.py
"""Generate an error‑analysis report for DeepGuard AI.

The script reads `ai/evaluation/results/evaluation_report.csv` (produced by
`evaluate.py`) and creates a plain‑text report `error_report.txt` in the same
`results/` folder.  The report contains:

- Lists of **False Positives** (predicted Fake but actually Real)
- Lists of **False Negatives** (predicted Real but actually Fake)
- The **lowest‑confidence predictions** (regardless of correctness)
- The **highest‑confidence incorrect predictions** (most confident mistakes)

For each entry we include:
    * filename
    * ground truth label (Real = 0, Fake = 1)
    * predicted label
    * confidence for the predicted class (the model’s probability for the
      class it chose)

Usage:
    python error_analysis.py
"""

import csv
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).parent / "results"
CSV_PATH = RESULTS_DIR / "evaluation_report.csv"
REPORT_PATH = RESULTS_DIR / "error_report.txt"

if not CSV_PATH.is_file():
    raise FileNotFoundError(f"Evaluation report not found at {CSV_PATH}")

# Load rows, keep only those where inference succeeded
rows = []
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["predicted"] in ("", None):
            continue
        rows.append({
            "filename": row.get("filename"),
            "ground_truth": int(row.get("ground_truth")),
            "prediction": int(row.get("predicted")),
            "prob_real": float(row.get("prob_real") or 0.0),
            "prob_fake": float(row.get("prob_fake") or 0.0),
        })

if not rows:
    raise ValueError("No successful inference rows available for error analysis.")

# Helper to get confidence of the predicted class
def predicted_confidence(r):
    return r["prob_fake"] if r["prediction"] == 1 else r["prob_real"]

# Separate false positives and false negatives
false_positives = [r for r in rows if r["prediction"] == 1 and r["ground_truth"] == 0]
false_negatives = [r for r in rows if r["prediction"] == 0 and r["ground_truth"] == 1]

# Lowest‑confidence predictions (sorted ascending by confidence)
rows_by_conf = sorted(rows, key=predicted_confidence)
lowest_conf = rows_by_conf[:5]  # show 5 lowest‑confidence examples

# Highest‑confidence incorrect predictions (sorted descending by confidence)
incorrect = [r for r in rows if r["prediction"] != r["ground_truth"]]
incorrect_by_conf = sorted(incorrect, key=predicted_confidence, reverse=True)
highest_conf_incorrect = incorrect_by_conf[:5]  # top 5 most confident mistakes

# Build report string
lines = []
lines.append("Error‑Analysis Report")
lines.append("====================\n")

def fmt_entry(r):
    gt = "Real" if r["ground_truth"] == 0 else "Fake"
    pred = "Real" if r["prediction"] == 0 else "Fake"
    conf = predicted_confidence(r) * 100  # percentage
    return f"{r['filename']}: ground truth={gt}, prediction={pred}, confidence={conf:.2f}%"

# False Positives
lines.append("False Positives (predicted Fake, actually Real):")
if false_positives:
    for r in false_positives:
        lines.append("  - " + fmt_entry(r))
else:
    lines.append("  (none)")
lines.append("")

# False Negatives
lines.append("False Negatives (predicted Real, actually Fake):")
if false_negatives:
    for r in false_negatives:
        lines.append("  - " + fmt_entry(r))
else:
    lines.append("  (none)")
lines.append("")

# Lowest‑confidence predictions
lines.append("Lowest‑confidence predictions (any class):")
for r in lowest_conf:
    lines.append("  - " + fmt_entry(r))
lines.append("")

# Highest‑confidence incorrect predictions
lines.append("Highest‑confidence incorrect predictions (most confident mistakes):")
if highest_conf_incorrect:
    for r in highest_conf_incorrect:
        lines.append("  - " + fmt_entry(r))
else:
    lines.append("  (none)")
lines.append("")

REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
print(f"Error‑analysis report saved to {REPORT_PATH}")
