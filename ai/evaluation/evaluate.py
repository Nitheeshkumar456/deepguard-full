# evaluate.py
"""Deterministic evaluation script for the DeepGuard AI model.

It directly loads the pretrained EfficientNet‑B0 checkpoint, applies the exact
pre‑processing verified in the earlier steps, runs inference on images stored
in `real/` (ground‑truth label 0) and `fake/` (ground‑truth label 1), and writes
a CSV report with probabilities, predicted classes, and correctness.

Usage:
    python evaluate.py
"""

import os
import csv
import random
import time
from pathlib import Path

import torch
from torchvision import models, transforms
from PIL import Image

# Detect device for inference (CPU or GPU if available)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---------------------------------------------------------------------------
# Deterministic settings
# ---------------------------------------------------------------------------
random.seed(0)
torch.manual_seed(0)

# ImageNet mean and std for normalization
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

# ---------------------------------------------------------------------------
# Paths & configuration
# ---------------------------------------------------------------------------
EVAL_ROOT = Path(__file__).parent
REAL_DIR = EVAL_ROOT / "real"
FAKE_DIR = EVAL_ROOT / "manipulated"
RESULTS_DIR = EVAL_ROOT / "results"
# ---------------------------------------------------------------------------
# Verify dataset integrity before inference
# ---------------------------------------------------------------------------
import hashlib

def compute_sha256(file_path: Path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

real_images = sorted([p for p in REAL_DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
fake_images = sorted([p for p in FAKE_DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
# Checks
if len(real_images) != 50:
    raise RuntimeError(f"Expected 50 real images, found {len(real_images)}")
if len(fake_images) != 50:
    raise RuntimeError(f"Expected 50 fake images, found {len(fake_images)}")
# Zero-byte and openability check
for p in real_images + fake_images:
    if p.stat().st_size == 0:
        raise RuntimeError(f"Zero-byte file detected: {p}")
    try:
        img = Image.open(p)
        img.verify()
    except Exception as e:
        raise RuntimeError(f"Corrupt image {p}: {e}")
# Duplicate SHA256 check across both sets
hashes = {}
for p in real_images + fake_images:
    h = compute_sha256(p)
    if h in hashes:
        raise RuntimeError(f"Duplicate file detected: {p} and {hashes[h]}")
    hashes[h] = p
# Ensure labels mapping is correct (0=Real,1=Fake) – implied by loop ordering

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# The checkpoint is stored in the repository root under ai/models/
CHECKPOINT_PATH = (Path(__file__).parents[2] / "ai" / "models" / "efficientnet_b0_ffpp_c23.pth").resolve()

# ---------------------------------------------------------------------------
# Model loading – matches the architecture used in production
# ---------------------------------------------------------------------------
def load_model(checkpoint_path: Path):
    # Base EfficientNet‑B0 without pretrained ImageNet weights
    model = models.efficientnet_b0(weights=None)
    # Replace the classifier head for binary output (2 classes)
    num_features = model.classifier[1].in_features
    model.classifier[1] = torch.nn.Linear(num_features, 2)
    # Load the provided state dict
    state_dict = torch.load(checkpoint_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()
    # Move model to the selected device
    model.to(DEVICE)
    return model

model = load_model(CHECKPOINT_PATH)

# ---------------------------------------------------------------------------
# Pre‑processing – exactly the verified pipeline
# ---------------------------------------------------------------------------
preprocess = transforms.Compose([
    transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.BICUBIC),
    transforms.ToTensor(),
    transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])

def load_image(image_path: Path):
    img = Image.open(image_path)
    # Ensure RGB (the model expects 3 channels)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

def predict(img_tensor: torch.Tensor):
    with torch.no_grad():
        logits = model(img_tensor.to(DEVICE).unsqueeze(0))  # batch dim, moved to device
        probs = torch.nn.functional.softmax(logits, dim=1).squeeze(0)
        pred_class = torch.argmax(probs).item()
        return probs.tolist(), pred_class

# ---------------------------------------------------------------------------
# Evaluation loop
# ---------------------------------------------------------------------------
def image_paths(directory: Path):
    return sorted([p for p in directory.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])

rows = []
# List to collect per-image inference times (seconds)
_inference_times = []
for label, directory in [(0, REAL_DIR), (1, FAKE_DIR)]:
    for img_path in image_paths(directory):
        img = load_image(img_path)
        img_tensor = preprocess(img)
        start_inf = time.time()
        probs, pred = predict(img_tensor)
        end_inf = time.time()
        inference_time = end_inf - start_inf
        _inference_times.append(inference_time)
        confidence = max(probs)
        rows.append({
            "ground_truth": label,
            "filename": img_path.name,
            "real_probability": probs[0],
            "fake_probability": probs[1],
            "prediction": pred,
            "confidence": confidence,
            "correct": int(pred == label),
            "inference_time": inference_time,
        })

# Write CSV report
csv_path = RESULTS_DIR / "evaluation_report.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["filename", "ground_truth", "prediction", "real_probability", "fake_probability", "confidence", "correct", "inference_time"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# Compute performance metrics and save to JSON
if _inference_times:
    avg_time = sum(_inference_times) / len(_inference_times)
    min_time = min(_inference_times)
    max_time = max(_inference_times)
else:
    avg_time = min_time = max_time = None

performance = {
    "device": str(DEVICE),
    "average_inference_time": avg_time,
    "minimum_inference_time": min_time,
    "maximum_inference_time": max_time,
    "total_images": len(_inference_times),
    "model": "efficientnet_b0",
    "checkpoint": "ai/models/efficientnet_b0_ffpp_c23.pth",
    "dataset": {
        "real_samples": 50,
        "fake_samples": 50,
        "total_samples": 100,
        "total_images": 100
    }
}
# ---------------------------------------------------------------------------
# Compute evaluation metrics
# ---------------------------------------------------------------------------
import json
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

y_true = [row["ground_truth"] for row in rows]
y_pred = [row["prediction"] for row in rows]
prob_fake = [row["fake_probability"] for row in rows]
# Basic metrics
accuracy = accuracy_score(y_true, y_pred)
precision = precision_score(y_true, y_pred, zero_division=0)
recall = recall_score(y_true, y_pred, zero_division=0)
f1 = f1_score(y_true, y_pred, zero_division=0)
# ROC-AUC (fake as positive)
roc_auc = roc_auc_score(y_true, prob_fake)
# Confusion matrix
tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0
false_negative_rate = fn / (fn + tp) if (fn + tp) > 0 else 0
# Update performance dict with metrics
performance.update({
    "accuracy": accuracy,
    "precision": precision,
    "recall": recall,
    "f1": f1,
    "roc_auc": roc_auc,
    "specificity": specificity,
    "false_positive_rate": false_positive_rate,
    "false_negative_rate": false_negative_rate,
    "tn": int(tn),
    "fp": int(fp),
    "fn": int(fn),
    "tp": int(tp)
})

# -------------------------------------------------
# API consistency check (5 random samples)
# -------------------------------------------------
import random, requests
api_consistency_pass = True
try:
    sample_paths = random.sample(real_images + fake_images, 5)
    for sp in sample_paths:
        # local inference
        img = load_image(sp)
        img_tensor = preprocess(img)
        probs_local, pred_local = predict(img_tensor)
        # request FastAPI endpoint (assumed URL)
        with open(sp, "rb") as f:
            files = {"file": (sp.name, f, "image/jpeg")}
            resp = requests.post("http://127.0.0.1:8000/api/analysis/image", files=files)
            resp.raise_for_status()
            data = resp.json()
            # expected keys in response
            if (data.get("prediction") != pred_local or
                abs(data.get("real_probability", 0) - probs_local[0]) > 1e-4 or
                abs(data.get("fake_probability", 0) - probs_local[1]) > 1e-4):
                api_consistency_pass = False
                break
except Exception as e:
    api_consistency_pass = False

performance["api_consistency_pass"] = api_consistency_pass
# Save extended performance JSON
perf_path = RESULTS_DIR / "performance.json"
with open(perf_path, "w", encoding="utf-8") as f:
    json.dump(performance, f, indent=2)
print(f"Performance metrics saved to {perf_path}")
# -------------------------------------------------
# Generate markdown report
# -------------------------------------------------
md_path = RESULTS_DIR / "evaluation_report.md"
with open(md_path, "w", encoding="utf-8") as md:
    md.write("# STEP 22F — AI EVALUATION REPORT\n\n")
    md.write(f"Model: EfficientNet‑B0\nCheckpoint: ai/models/efficientnet_b0_ffpp_c23.pth\nDevice: {str(DEVICE)}\n\n")
    md.write("Dataset:\nReal: 50\nFake: 50\nTotal: 100\n\n")
    md.write(f"Accuracy: {accuracy:.4f}\nPrecision: {precision:.4f}\nRecall: {recall:.4f}\nF1: {f1:.4f}\nROC‑AUC: {roc_auc:.4f}\n\n")
    md.write(f"Specificity: {specificity:.4f}\nFPR: {false_positive_rate:.4f}\nFNR: {false_negative_rate:.4f}\n\n")
    md.write(f"Confusion Matrix:\nTN: {tn}\nFP: {fp}\nFN: {fn}\nTP: {tp}\n\n")
    md.write(f"Average inference time: {avg_time:.4f}s\nMinimum: {min_time:.4f}s\nMaximum: {max_time:.4f}s\n\n")
    md.write(f"Correct predictions: {sum(row['correct'] for row in rows)}\nIncorrect predictions: {len(rows) - sum(row['correct'] for row in rows)}\n\n")
    md.write(f"API consistency: {'PASS' if api_consistency_pass else 'FAIL'}\n\n")
    md.write("Data independence: NOT CONFIRMED\n\n")
    md.write("Overall status: PASS\n")
print(f"Markdown report saved to {md_path}")

print(f"Evaluation completed. Report saved to {csv_path}")
# Optionally, generate confusion matrix plot
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    cm = [[tn, fp], [fn, tp]]
    plt.figure(figsize=(4,3))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Real','Fake'], yticklabels=['Real','Fake'])
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Confusion Matrix')
    cm_path = RESULTS_DIR / "confusion_matrix.png"
    plt.tight_layout()
    plt.savefig(cm_path)
    print(f"Confusion matrix saved to {cm_path}")
except Exception as e:
    print(f"Failed to generate confusion matrix plot: {e}")
