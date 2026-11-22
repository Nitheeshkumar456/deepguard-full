"""
evaluate_audio_upgrade.py — Comprehensive Evaluation and Comparison of Audio Deepfake Models.

Compares:
  1. Original Baseline Model: AASIST (Raw Waveform Graph Attention Network)
  2. Retrained / Improved Model: DeepGuard-AudioSpecNet-v2 (Log-Mel + Delta + Delta-Delta with SE-ResNet)
  3. Calibrated Dual-Ensemble: AASIST + SpecNet-v2 Calibrated Fusion

Evaluates on:
  - Standard Test Split (Unseen LibriSpeech speakers + ASVspoof/neural vocoder)
  - Challenge 1: Unseen Speakers (Completely isolated identities)
  - Challenge 2: Recording Devices (Telephone bandwidth, MEMS mics, USB headsets)
  - Challenge 3: Compressed Audio (MP3 64kbps, MP3 128kbps, OGG Vorbis)
  - Challenge 4: Different Languages (French, Spanish, German, Italian, Mandarin)
  - Challenge 5: Unseen Spoofing Methods (Diffusion vocoders, cloaked phase perturbations)
  - Consolidated Benchmark (Aggregate across all test splits)

Metrics Computed:
  - Accuracy
  - Precision
  - Recall
  - F1-Score
  - ROC-AUC
  - Equal Error Rate (EER)
  - False Positive Rate (FPR)
  - False Negative Rate (FNR)
"""

import os
import sys
import json
import time
from typing import List, Dict, Any, Tuple

import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, roc_curve
from scipy.interpolate import interp1d

# Paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AI_DIR = os.path.join(ROOT_DIR, "ai")
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

sys.path.insert(0, os.path.join(BACKEND_DIR, "app", "services"))
sys.path.insert(0, os.path.join(AI_DIR, "src"))

from aasist_model import AASISTAudioModel, DEFAULT_AASIST_CONFIG
from audio_specnet_model import DeepGuardAudioSpecNet, extract_dynamic_spectrogram

AASIST_CHECKPOINT = os.path.join(AI_DIR, "models", "AASIST.pth")
SPECNET_CHECKPOINT = os.path.join(AI_DIR, "models", "deepguard_audio_v2.pth")
DATASET_ROOT = os.path.join(AI_DIR, "datasets", "audio_v2_dataset")


def compute_eer(y_true: np.ndarray, y_scores: np.ndarray) -> float:
    """Computes Equal Error Rate (EER) where FPR == FNR."""
    if len(np.unique(y_true)) < 2:
        return 0.0

    fpr, tpr, thresholds = roc_curve(y_true, y_scores, pos_label=1)
    fnr = 1.0 - tpr

    # Find the point where FPR and FNR intersect
    idx = np.nanargmin(np.abs(fpr - fnr))
    eer = (fpr[idx] + fnr[idx]) / 2.0
    return float(eer)


def compute_metrics(y_true: List[int], y_probs: List[float], threshold: float = 0.5) -> Dict[str, float]:
    """Computes all required evaluation metrics."""
    y_true_arr = np.array(y_true, dtype=int)
    y_probs_arr = np.array(y_probs, dtype=float)
    y_pred_arr = (y_probs_arr >= threshold).astype(int)

    acc = float(accuracy_score(y_true_arr, y_pred_arr))
    prec = float(precision_score(y_true_arr, y_pred_arr, zero_division=0))
    rec = float(recall_score(y_true_arr, y_pred_arr, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred_arr, zero_division=0))

    try:
        auc = float(roc_auc_score(y_true_arr, y_probs_arr))
    except Exception:
        auc = 0.50

    eer = compute_eer(y_true_arr, y_probs_arr)

    # Confusion matrix elements for FPR and FNR
    tn = np.sum((y_true_arr == 0) & (y_pred_arr == 0))
    fp = np.sum((y_true_arr == 0) & (y_pred_arr == 1))
    fn = np.sum((y_true_arr == 1) & (y_pred_arr == 0))
    tp = np.sum((y_true_arr == 1) & (y_pred_arr == 1))

    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(auc, 4),
        "eer": round(eer, 4),
        "fpr": round(fpr, 4),
        "fnr": round(fnr, 4),
        "total_samples": len(y_true),
        "real_count": int(np.sum(y_true_arr == 0)),
        "fake_count": int(np.sum(y_true_arr == 1)),
    }


def load_aasist(device: torch.device) -> AASISTAudioModel:
    model = AASISTAudioModel(DEFAULT_AASIST_CONFIG)
    state_dict = torch.load(AASIST_CHECKPOINT, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def load_specnet(device: torch.device) -> Tuple[DeepGuardAudioSpecNet, float]:
    model = DeepGuardAudioSpecNet(num_classes=2)
    checkpoint = torch.load(SPECNET_CHECKPOINT, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    calibrated_temp = float(checkpoint.get("calibrated_temperature", 1.0))
    model.to(device)
    model.eval()
    return model, calibrated_temp


def read_and_prepare_audio(file_path: str, target_samples: int = 64600) -> np.ndarray:
    try:
        data, sr = sf.read(file_path)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
    except Exception:
        data = np.zeros(target_samples, dtype=np.float32)

    if len(data) < target_samples:
        data = np.pad(data, (0, target_samples - len(data)), mode="wrap")
    elif len(data) > target_samples:
        data = data[:target_samples]
    return data.astype(np.float32)


def evaluate_all():
    print("=" * 80)
    print(" DEEPGUARD AI AUDIO DETECTION — COMPREHENSIVE BENCHMARK & MODEL COMPARISON")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    print(f"Loading AASIST from: {AASIST_CHECKPOINT}")
    print(f"Loading SpecNet v2 from: {SPECNET_CHECKPOINT}")

    aasist_model = load_aasist(device)
    specnet_model, cal_temp = load_specnet(device)
    print(f"SpecNet Calibrated Temperature: {cal_temp:.4f}\n")

    test_splits = {
        "Standard Test Set": "test",
        "Challenge 1: Unseen Speakers": "test_unseen_speakers",
        "Challenge 2: Different Recording Devices": "test_different_devices",
        "Challenge 3: Compressed Audio": "test_compressed_audio",
        "Challenge 4: Different Languages": "test_different_languages",
        "Challenge 5: Unseen Spoofing Methods": "test_unseen_spoofing",
    }

    results = {
        "splits": {},
        "consolidated": {},
    }

    # Consolidated pools
    all_y_true = []
    all_aasist_probs = []
    all_specnet_probs = []
    all_ensemble_probs = []

    for split_label, split_dir in test_splits.items():
        split_path = os.path.join(DATASET_ROOT, split_dir)
        real_files = [os.path.join(split_path, "real", f) for f in os.listdir(os.path.join(split_path, "real")) if f.endswith(".wav")]
        fake_files = [os.path.join(split_path, "fake", f) for f in os.listdir(os.path.join(split_path, "fake")) if f.endswith(".wav")]

        y_true = [0] * len(real_files) + [1] * len(fake_files)
        files = real_files + fake_files

        aasist_probs = []
        specnet_probs = []
        ensemble_probs = []

        for fpath in files:
            waveform = read_and_prepare_audio(fpath, target_samples=64600)

            # 1. AASIST Inference: input (1, 64600), output logits: [spoof(0), bonafide(1)]
            wave_tensor = torch.from_numpy(waveform).unsqueeze(0).to(device)
            with torch.no_grad():
                _, aasist_logits = aasist_model(wave_tensor)
                aasist_p = F.softmax(aasist_logits, dim=1).cpu().numpy()[0]
                p_aasist_fake = float(aasist_p[0])  # index 0 is spoof

            # 2. SpecNet v2 Inference: input (1, 3, 80, 128), output logits: [real(0), fake(1)]
            spec = extract_dynamic_spectrogram(waveform, sr=16000, target_length=128)
            spec_tensor = torch.from_numpy(spec).unsqueeze(0).to(device)
            with torch.no_grad():
                _, specnet_logits = specnet_model(spec_tensor)
                # Calibrated with temperature
                cal_logits = specnet_logits / cal_temp
                specnet_p = F.softmax(cal_logits, dim=1).cpu().numpy()[0]
                p_specnet_fake = float(specnet_p[1])  # index 1 is fake

            # 3. Dual-Ensemble: Calibrated fusion
            # SpecNet provides acoustic spectrogram stability under noise/compression,
            # AASIST provides raw-waveform phase sensitivity for vocoder synthesis.
            p_ensemble_fake = float(0.45 * p_aasist_fake + 0.55 * p_specnet_fake)

            aasist_probs.append(p_aasist_fake)
            specnet_probs.append(p_specnet_fake)
            ensemble_probs.append(p_ensemble_fake)

        all_y_true.extend(y_true)
        all_aasist_probs.extend(aasist_probs)
        all_specnet_probs.extend(specnet_probs)
        all_ensemble_probs.extend(ensemble_probs)

        # Compute metrics for this split
        m_aasist = compute_metrics(y_true, aasist_probs)
        m_specnet = compute_metrics(y_true, specnet_probs)
        m_ensemble = compute_metrics(y_true, ensemble_probs)

        results["splits"][split_label] = {
            "AASIST (Original)": m_aasist,
            "DeepGuard-AudioSpecNet-v2 (Retrained)": m_specnet,
            "Calibrated Dual-Ensemble (Upgraded System)": m_ensemble,
        }

        print(f"=== {split_label} (N={len(y_true)}, Real={len(real_files)}, Fake={len(fake_files)}) ===")
        print(f"  {'Model':<35} | {'Acc':<6} | {'Prec':<6} | {'Rec':<6} | {'F1':<6} | {'AUC':<6} | {'EER':<6} | {'FPR':<6} | {'FNR':<6}")
        print("  " + "-" * 90)
        for model_k, metrics_v in results["splits"][split_label].items():
            print(f"  {model_k:<35} | {metrics_v['accuracy']*100:5.1f}% | {metrics_v['precision']*100:5.1f}% | {metrics_v['recall']*100:5.1f}% | {metrics_v['f1']:5.3f} | {metrics_v['roc_auc']:5.3f} | {metrics_v['eer']*100:5.1f}% | {metrics_v['fpr']*100:5.1f}% | {metrics_v['fnr']*100:5.1f}%")
        print()

    # Consolidated Metrics across all 80 evaluation audio files
    cons_aasist = compute_metrics(all_y_true, all_aasist_probs)
    cons_specnet = compute_metrics(all_y_true, all_specnet_probs)
    cons_ensemble = compute_metrics(all_y_true, all_ensemble_probs)

    results["consolidated"] = {
        "AASIST (Original)": cons_aasist,
        "DeepGuard-AudioSpecNet-v2 (Retrained)": cons_specnet,
        "Calibrated Dual-Ensemble (Upgraded System)": cons_ensemble,
    }

    print("=" * 80)
    print(f" CONSOLIDATED BENCHMARK ACROSS ALL TEST DOMAINS (N={len(all_y_true)})")
    print("=" * 80)
    print(f"  {'Model':<35} | {'Acc':<6} | {'Prec':<6} | {'Rec':<6} | {'F1':<6} | {'AUC':<6} | {'EER':<6} | {'FPR':<6} | {'FNR':<6}")
    print("  " + "-" * 90)
    for model_k, metrics_v in results["consolidated"].items():
        print(f"  {model_k:<35} | {metrics_v['accuracy']*100:5.1f}% | {metrics_v['precision']*100:5.1f}% | {metrics_v['recall']*100:5.1f}% | {metrics_v['f1']:5.3f} | {metrics_v['roc_auc']:5.3f} | {metrics_v['eer']*100:5.1f}% | {metrics_v['fpr']*100:5.1f}% | {metrics_v['fnr']*100:5.1f}%")
    print("=" * 80)

    # Save benchmark JSON
    out_json = os.path.join(AI_DIR, "evaluation", "audio_model_benchmark_results.json")
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved benchmark results to: {out_json}")


if __name__ == "__main__":
    evaluate_all()

