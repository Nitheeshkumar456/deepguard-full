"""
evaluate_upgraded.py — Comprehensive Evaluation of Original vs Upgraded Model.

Runs both the original (efficientnet_b0_ffpp_c23.pth) and the upgraded
(efficientnet_b0_v2_finetuned.pth) models on the test set and on the
original 100-image evaluation corpus, computing full metrics:
  - Accuracy, Precision, Recall, F1-Score
  - ROC-AUC, Specificity, FPR, FNR
  - Confusion matrix
  - Per-threshold sensitivity analysis

Also evaluates the new morphing detector on the 50-real + 50-manipulated
evaluation images to provide an honest score for the new capabilities.

Usage:
    python evaluate_upgraded.py
    python evaluate_upgraded.py --model-path ai/models/efficientnet_b0_v2_finetuned.pth
    python evaluate_upgraded.py --only-original     # Evaluate original only
"""

import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms, datasets
from torch.utils.data import DataLoader
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MODELS_DIR = PROJECT_ROOT / "ai" / "models"
DATASETS_DIR = PROJECT_ROOT / "ai" / "datasets"
EVAL_DIR = PROJECT_ROOT / "ai" / "evaluation"
RESULTS_DIR = SCRIPT_DIR / "results"

ORIGINAL_CHECKPOINT = MODELS_DIR / "efficientnet_b0_ffpp_c23.pth"
UPGRADED_CHECKPOINT = MODELS_DIR / "efficientnet_b0_v2_finetuned.pth"

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
IMG_SIZE = 224


# ─────────────────────────────────────────────────────────────────────────────
# Model definition (must match ai_service.py)
# ─────────────────────────────────────────────────────────────────────────────

class DeepGuardModel(nn.Module):
    def __init__(self):
        super().__init__()
        base = models.efficientnet_b0(weights=None)
        self.features = base.features
        self.avgpool = base.avgpool
        self.classifier = base.classifier
        self.classifier[1] = nn.Linear(self.classifier[1].in_features, 2)

    def forward(self, x):
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x


def load_model(checkpoint_path: Path, device: torch.device) -> nn.Module:
    model = DeepGuardModel()
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    state_dict = torch.load(str(checkpoint_path), map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    logger.info("Loaded: %s", checkpoint_path.name)
    return model


def get_transforms() -> transforms.Compose:
    return transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE), interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> Dict:
    accuracy = float(np.mean(y_true == y_pred))
    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    try:
        from sklearn.metrics import roc_auc_score
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc_auc = 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "specificity": round(specificity, 4),
        "fpr": round(fpr, 4),
        "fnr": round(fnr, 4),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "total": len(y_true),
    }


@torch.no_grad()
def evaluate_on_loader(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> Dict:
    all_labels, all_preds, all_probs = [], [], []
    latencies = []

    for inputs, labels in loader:
        inputs = inputs.to(device)
        t0 = time.perf_counter()
        outputs = model(inputs)
        latencies.append(time.perf_counter() - t0)

        probs = torch.softmax(outputs, dim=1)
        _, predicted = torch.max(outputs, 1)
        all_labels.extend(labels.numpy())
        all_preds.extend(predicted.cpu().numpy())
        all_probs.extend(probs[:, 1].cpu().numpy())

    metrics = compute_metrics(
        np.array(all_labels),
        np.array(all_preds),
        np.array(all_probs),
    )
    metrics["avg_latency_ms"] = round(1000 * float(np.mean(latencies)), 2)
    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# 100-image direct evaluation (no DataLoader needed)
# ─────────────────────────────────────────────────────────────────────────────

@torch.no_grad()
def evaluate_on_eval_corpus(
    model: nn.Module,
    device: torch.device,
    tfm: transforms.Compose,
) -> Dict:
    """
    Evaluate on the original 50-real + 50-fake evaluation corpus.
    Returns metrics dict or None if directories don't exist.
    """
    real_dir = EVAL_DIR / "real"
    fake_dir = EVAL_DIR / "manipulated"

    if not real_dir.is_dir() or not fake_dir.is_dir():
        return {}

    ext = {".jpg", ".jpeg", ".png"}
    real_files = [f for f in sorted(real_dir.iterdir()) if f.suffix.lower() in ext]
    fake_files = [f for f in sorted(fake_dir.iterdir()) if f.suffix.lower() in ext]

    all_labels, all_preds, all_probs = [], [], []
    latencies = []

    for files, label in [(real_files, 0), (fake_files, 1)]:
        for f in files:
            try:
                img = Image.open(f).convert("RGB")
                tensor = tfm(img).unsqueeze(0).to(device)
                t0 = time.perf_counter()
                out = model(tensor)
                latencies.append(time.perf_counter() - t0)
                prob = torch.softmax(out, dim=1).squeeze()
                pred = int(torch.argmax(prob).item())
                all_labels.append(label)
                all_preds.append(pred)
                all_probs.append(float(prob[1].item()))
            except Exception as e:
                logger.warning("Skip %s: %s", f.name, e)

    if not all_labels:
        return {}

    metrics = compute_metrics(
        np.array(all_labels),
        np.array(all_preds),
        np.array(all_probs),
    )
    metrics["avg_latency_ms"] = round(1000 * float(np.mean(latencies)), 2)
    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# Morphing detector evaluation
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_morphing_detector() -> Dict:
    """
    Evaluate the MorphingDetector on 50 real + 50 manipulated evaluation images.
    Returns accuracy/precision/recall/F1 for the morphing composite score
    at threshold = 0.5.
    """
    try:
        import cv2
        sys.path.insert(0, str(PROJECT_ROOT / "backend"))
        from app.services.morphing_detector import get_morphing_detector

        detector = get_morphing_detector()
        real_dir = EVAL_DIR / "real"
        fake_dir = EVAL_DIR / "manipulated"
        ext = {".jpg", ".jpeg", ".png"}

        all_labels, all_preds, all_probs = [], [], []

        for files, label in [(sorted(real_dir.glob("*.jpg")), 0),
                              (sorted(fake_dir.glob("*.jpg")), 1)]:
            for f in files:
                try:
                    bgr = cv2.imread(str(f))
                    if bgr is None:
                        continue
                    result = detector.analyze(bgr, face_bbox_xywh=None)
                    score = result["composite_morphing_score"]
                    pred = 1 if score >= 0.5 else 0
                    all_labels.append(label)
                    all_preds.append(pred)
                    all_probs.append(score)
                except Exception as e:
                    logger.debug("Morphing eval error on %s: %s", f.name, e)

        if not all_labels:
            return {"error": "No images evaluated"}

        return compute_metrics(
            np.array(all_labels),
            np.array(all_preds),
            np.array(all_probs),
        )
    except Exception as e:
        logger.warning("Morphing detector evaluation failed: %s", e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Threshold sweep
# ─────────────────────────────────────────────────────────────────────────────

def threshold_sweep(y_true: List[int], y_prob: List[float]) -> List[Dict]:
    results = []
    for thresh in [0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7]:
        y_pred = [1 if p >= thresh else 0 for p in y_prob]
        m = compute_metrics(np.array(y_true), np.array(y_pred), np.array(y_prob))
        m["threshold"] = thresh
        results.append(m)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DeepGuard AI — Model Evaluation")
    parser.add_argument("--model-path", type=str, default=None,
                        help="Path to upgraded model checkpoint (default: auto-detect)")
    parser.add_argument("--only-original", action="store_true",
                        help="Only evaluate the original model")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", type=str, default="auto")
    args = parser.parse_args()

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    logger.info("Device: %s", device)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    tfm = get_transforms()

    # ── Determine upgraded model path ────────────────────────────────────────
    if args.model_path:
        upgraded_path = Path(args.model_path)
    else:
        upgraded_path = UPGRADED_CHECKPOINT

    report = {
        "device": str(device),
        "original_checkpoint": str(ORIGINAL_CHECKPOINT),
        "upgraded_checkpoint": str(upgraded_path),
        "upgraded_exists": upgraded_path.is_file(),
    }

    # ── 1. Original model — 100-image eval corpus ────────────────────────────
    logger.info("\n" + "=" * 70)
    logger.info("ORIGINAL MODEL — Evaluation Corpus (100 images)")
    logger.info("=" * 70)
    orig_model = load_model(ORIGINAL_CHECKPOINT, device)
    orig_eval = evaluate_on_eval_corpus(orig_model, device, tfm)
    report["original_eval_corpus"] = orig_eval
    for k, v in orig_eval.items():
        logger.info("  %-20s %s", k + ":", v)

    # ── 2. Original model — test set ─────────────────────────────────────────
    test_dir = DATASETS_DIR / "test"
    orig_test = {}
    if test_dir.is_dir() and any(test_dir.iterdir()):
        logger.info("\nOriginal Model — Test Set")
        test_ds = datasets.ImageFolder(str(test_dir), transform=tfm)
        test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
        orig_test = evaluate_on_loader(orig_model, test_loader, device)
        report["original_test_set"] = orig_test
        for k, v in orig_test.items():
            logger.info("  %-20s %s", k + ":", v)

    del orig_model
    torch.cuda.empty_cache() if torch.cuda.is_available() else None

    if args.only_original:
        logger.info("\n[--only-original] Skipping upgraded model evaluation.")
        out = RESULTS_DIR / "evaluation_report_v2.json"
        with open(out, "w") as f:
            json.dump(report, f, indent=2)
        logger.info("Report saved: %s", out)
        return

    # ── 3. Upgraded model — test set ─────────────────────────────────────────
    if upgraded_path.is_file():
        logger.info("\n" + "=" * 70)
        logger.info("UPGRADED MODEL (%s)", upgraded_path.name)
        logger.info("=" * 70)

        upg_model = load_model(upgraded_path, device)
        upg_eval = evaluate_on_eval_corpus(upg_model, device, tfm)
        report["upgraded_eval_corpus"] = upg_eval
        logger.info("\nUpgraded Model — Evaluation Corpus (100 images)")
        for k, v in upg_eval.items():
            logger.info("  %-20s %s", k + ":", v)

        upg_test = {}
        if test_dir.is_dir() and any(test_dir.iterdir()):
            logger.info("\nUpgraded Model — Test Set")
            upg_test = evaluate_on_loader(upg_model, test_loader, device)
            report["upgraded_test_set"] = upg_test
            for k, v in upg_test.items():
                logger.info("  %-20s %s", k + ":", v)

        del upg_model

        # ── 4. Comparison table ─────────────────────────────────────────────
        logger.info("\n" + "=" * 70)
        logger.info("COMPARISON: Original vs Upgraded (Evaluation Corpus)")
        logger.info("=" * 70)
        logger.info("  %-18s  %10s  %10s  %10s", "Metric", "Original", "Upgraded", "Delta")
        logger.info("  " + "-" * 60)

        comparison = {}
        for metric in ["accuracy", "precision", "recall", "f1_score", "roc_auc", "specificity", "fpr", "fnr"]:
            orig_v = orig_eval.get(metric, 0.0)
            upg_v = upg_eval.get(metric, 0.0)
            delta = round(upg_v - orig_v, 4)
            direction = "UP" if (delta > 0 and metric not in ["fpr", "fnr"]) or (delta < 0 and metric in ["fpr", "fnr"]) else ("DOWN" if delta != 0 else "SAME")
            logger.info("  %-18s  %10.4f  %10.4f  %+10.4f  [%s]",
                        metric, orig_v, upg_v, delta, direction)
            comparison[metric] = {"original": orig_v, "upgraded": upg_v, "delta": delta, "direction": direction}

        report["comparison"] = comparison

    else:
        logger.warning("Upgraded model not found at %s. Skipping comparison.", upgraded_path)
        report["upgraded_note"] = "Upgraded model not yet trained. Run train.py first."

    # ── 5. Morphing detector evaluation ─────────────────────────────────────
    logger.info("\n" + "=" * 70)
    logger.info("MORPHING DETECTOR — Signal-Only Evaluation (100 images)")
    logger.info("=" * 70)
    morphing_metrics = evaluate_morphing_detector()
    report["morphing_detector"] = morphing_metrics
    for k, v in morphing_metrics.items():
        logger.info("  %-20s %s", k + ":", v)

    # ── 6. Save report ────────────────────────────────────────────────────────
    out = RESULTS_DIR / "evaluation_report_v2.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("\nEvaluation report saved: %s", out)

    # ── 7. Print summary ──────────────────────────────────────────────────────
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY  (PRIMARY: Hold-Out Test Set | Secondary: Eval Corpus)")
    logger.info("=" * 70)
    logger.info("%-16s | %-20s | %-20s", "Model", "Test Set (165 imgs)", "Eval Corpus (100 imgs)")
    logger.info("-" * 65)

    orig_test  = report.get("original_test_set", {})
    upg_test   = report.get("upgraded_test_set", {})
    orig_eval  = report.get("original_eval_corpus", orig_eval or {})
    upg_corpus = report.get("upgraded_eval_corpus", {})

    if orig_test:
        logger.info("Original v1     | Acc:%.1f%% F1:%.4f AUC:%.4f | Acc:%.1f%% F1:%.4f AUC:%.4f",
                    orig_test.get("accuracy", 0) * 100, orig_test.get("f1_score", 0), orig_test.get("roc_auc", 0),
                    orig_eval.get("accuracy", 0) * 100, orig_eval.get("f1_score", 0), orig_eval.get("roc_auc", 0))
    if upg_test:
        logger.info("Upgraded v2     | Acc:%.1f%% F1:%.4f AUC:%.4f | Acc:%.1f%% F1:%.4f AUC:%.4f",
                    upg_test.get("accuracy", 0) * 100, upg_test.get("f1_score", 0), upg_test.get("roc_auc", 0),
                    upg_corpus.get("accuracy", 0) * 100, upg_corpus.get("f1_score", 0), upg_corpus.get("roc_auc", 0))
        if orig_test:
            delta_acc = (upg_test.get("accuracy", 0) - orig_test.get("accuracy", 0)) * 100
            delta_f1  = upg_test.get("f1_score", 0) - orig_test.get("f1_score", 0)
            delta_auc = upg_test.get("roc_auc", 0) - orig_test.get("roc_auc", 0)
            logger.info("Delta v2 vs v1  | Acc:%+.1f%%  F1:%+.4f  AUC:%+.4f",
                        delta_acc, delta_f1, delta_auc)
    if morphing_metrics and "accuracy" in morphing_metrics:
        logger.info("\nMorphing detect | Acc: %.1f%% | F1: %.4f | Recall: %.1f%%",
                    morphing_metrics.get("accuracy", 0) * 100,
                    morphing_metrics.get("f1_score", 0),
                    morphing_metrics.get("recall", 0) * 100)
    logger.info("\nNOTE: Eval corpus comparison is biased — original model was tuned on this corpus.")
    logger.info("      Test set (hold-out) is the definitive comparison.")


if __name__ == "__main__":
    main()
