"""
evaluate_audio.py — Independent Empirical Evaluation of DeepGuard AI Audio Detection Module.

Evaluates 20 Genuine human speech samples and 20 Manipulated audio samples across 4 forensic categories:
  - Category 1: AI-Generated / Neural Vocoder Synthetic Voices (HiFi-GAN / MelGAN style)
  - Category 2: Voice Cloning & Pitch Modulation (Phase vocoder dispersion)
  - Category 3: Audio Splicing & Cut-and-Paste (Spectral flux & energy discontinuities)
  - Category 4: Replay Attacks (Loudspeaker frequency cutoff & room reverberation)

Computes:
  - Accuracy, Precision, Recall, F1-Score, ROC-AUC
  - Confusion Matrix (TP, FP, TN, FN)
  - False Positive Rate (FPR), False Negative Rate (FNR)
  - Per-category breakdown & detection latency
"""

import os
import sys
import json
import time
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.audio_detector import run_audio_inference


def evaluate_audio_module():
    benchmark_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "datasets", "audio_benchmark"))
    genuine_dir = os.path.join(benchmark_dir, "genuine")
    manipulated_dir = os.path.join(benchmark_dir, "manipulated")

    genuine_files = sorted([os.path.join(genuine_dir, f) for f in os.listdir(genuine_dir) if f.endswith(".wav")])
    manipulated_files = sorted([os.path.join(manipulated_dir, f) for f in os.listdir(manipulated_dir) if f.endswith(".wav")])

    print("=" * 70)
    print(" DEEPGUARD AI AUDIO DETECTION MODULE — INDEPENDENT BENCHMARK EVALUATION")
    print("=" * 70)
    print(f"Genuine Samples:     {len(genuine_files)} (Ground Truth Class: 0 / Authentic)")
    print(f"Manipulated Samples: {len(manipulated_files)} (Ground Truth Class: 1 / Synthetic/Tampered)")
    print(f"Total Test Samples:  {len(genuine_files) + len(manipulated_files)}")
    print("-" * 70)

    y_true = []
    y_pred = []
    y_scores = []
    inference_times = []
    results_detail = []

    # 1. Evaluate Genuine Samples
    print("\n--- Evaluating Genuine Human Speech Samples ---")
    for f in genuine_files:
        t0 = time.time()
        res = run_audio_inference(f)
        elapsed_ms = (time.time() - t0) * 1000.0
        inference_times.append(elapsed_ms)

        pred_binary = 1 if res.prediction == "synthetic" else 0
        fake_score = res.probabilities.get("synthetic", 0.0)

        y_true.append(0)
        y_pred.append(pred_binary)
        y_scores.append(fake_score)

        status_str = "CORRECT [TN]" if pred_binary == 0 else "MISCLASSIFIED [FP]"
        print(f"  [GENUINE] {os.path.basename(f)}: pred={res.prediction:9s} conf={res.confidence:.4f} "
              f"p(fake)={fake_score:.4f} vc_score={res.voice_cloning_score:.4f} -> {status_str} ({elapsed_ms:.1f}ms)")

        results_detail.append({
            "filename": os.path.basename(f),
            "ground_truth": "authentic",
            "ground_truth_label": 0,
            "prediction": res.prediction,
            "predicted_label": pred_binary,
            "confidence": res.confidence,
            "synthetic_probability": fake_score,
            "voice_cloning_score": res.voice_cloning_score,
            "spectral_anomaly_score": res.spectral_anomaly_score,
            "splicing_score": getattr(res, "splicing_score", 0.0),
            "replay_attack_score": getattr(res, "replay_attack_score", 0.0),
            "inference_time_ms": round(elapsed_ms, 2),
            "correct": pred_binary == 0,
        })

    # 2. Evaluate Manipulated Samples
    print("\n--- Evaluating Manipulated & Synthetic Audio Samples ---")
    category_counts = {}
    category_correct = {}

    for f in manipulated_files:
        t0 = time.time()
        res = run_audio_inference(f)
        elapsed_ms = (time.time() - t0) * 1000.0
        inference_times.append(elapsed_ms)

        pred_binary = 1 if res.prediction == "synthetic" else 0
        fake_score = res.probabilities.get("synthetic", 0.0)

        y_true.append(1)
        y_pred.append(pred_binary)
        y_scores.append(fake_score)

        # Category determination
        basename = os.path.basename(f)
        if "vocoder" in basename:
            cat = "Synthetic Vocoder (TTS)"
        elif "cloned" in basename:
            cat = "Voice Cloning / Modulation"
        elif "spliced" in basename:
            cat = "Audio Splicing / Cut-Paste"
        elif "replay" in basename:
            cat = "Replay Attack / Coloration"
        else:
            cat = "Other Manipulated"

        category_counts[cat] = category_counts.get(cat, 0) + 1
        if pred_binary == 1:
            category_correct[cat] = category_correct.get(cat, 0) + 1

        status_str = "CORRECT [TP]" if pred_binary == 1 else "MISCLASSIFIED [FN]"
        print(f"  [MANIP]   {basename:22s} ({cat:25s}): pred={res.prediction:9s} conf={res.confidence:.4f} "
              f"p(fake)={fake_score:.4f} splice={getattr(res, 'splicing_score', 0.0):.3f} -> {status_str} ({elapsed_ms:.1f}ms)")

        results_detail.append({
            "filename": basename,
            "category": cat,
            "ground_truth": "synthetic",
            "ground_truth_label": 1,
            "prediction": res.prediction,
            "predicted_label": pred_binary,
            "confidence": res.confidence,
            "synthetic_probability": fake_score,
            "voice_cloning_score": res.voice_cloning_score,
            "spectral_anomaly_score": res.spectral_anomaly_score,
            "splicing_score": getattr(res, "splicing_score", 0.0),
            "replay_attack_score": getattr(res, "replay_attack_score", 0.0),
            "inference_time_ms": round(elapsed_ms, 2),
            "correct": pred_binary == 1,
        })

    # Metrics computation
    y_true_np = np.array(y_true)
    y_pred_np = np.array(y_pred)
    y_scores_np = np.array(y_scores)

    acc = float(accuracy_score(y_true_np, y_pred_np))
    prec = float(precision_score(y_true_np, y_pred_np, zero_division=0))
    rec = float(recall_score(y_true_np, y_pred_np, zero_division=0))
    f1 = float(f1_score(y_true_np, y_pred_np, zero_division=0))
    auc = float(roc_auc_score(y_true_np, y_scores_np))

    cm = confusion_matrix(y_true_np, y_pred_np)
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    mean_latency = float(np.mean(inference_times))

    print("\n" + "=" * 70)
    print(" EMPIRICAL EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Accuracy:           {acc * 100:.2f}% ({tp + tn}/{len(y_true)})")
    print(f"Precision:          {prec:.4f}")
    print(f"Recall:             {rec:.4f}")
    print(f"F1-Score:           {f1:.4f}")
    print(f"ROC-AUC:            {auc:.4f}")
    print(f"Confusion Matrix:   TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    print(f"False Positive Rate:{fpr * 100:.2f}% ({fp}/{fp + tn})")
    print(f"False Negative Rate:{fnr * 100:.2f}% ({fn}/{fn + tp})")
    print(f"Average Latency:    {mean_latency:.1f} ms / file")
    print("-" * 70)
    print(" CATEGORY-SPECIFIC BREAKDOWN:")
    for cat, total in category_counts.items():
        corr = category_correct.get(cat, 0)
        pct = (corr / total) * 100 if total > 0 else 0.0
        print(f"  - {cat:30s}: {corr}/{total} detected ({pct:.1f}%)")
    print("=" * 70)

    # Save results to json
    results_path = os.path.join(benchmark_dir, "audio_evaluation_results.json")
    summary = {
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_samples": len(y_true),
        "genuine_samples": len(genuine_files),
        "manipulated_samples": len(manipulated_files),
        "metrics": {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(auc, 4),
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "average_latency_ms": round(mean_latency, 2),
        },
        "category_breakdown": {
            cat: {
                "detected": category_correct.get(cat, 0),
                "total": category_counts[cat],
                "accuracy": round(category_correct.get(cat, 0) / category_counts[cat], 4),
            }
            for cat in category_counts
        },
        "sample_details": results_detail,
    }

    with open(results_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved empirical evaluation results to {results_path}")
    return summary


if __name__ == "__main__":
    evaluate_audio_module()

