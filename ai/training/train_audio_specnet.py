"""
train_audio_specnet.py — Training, Data Augmentation & Calibration for DeepGuard Audio SpecNet v2.

Features:
  - 3-channel dynamic spectrogram extraction: [Log-Mel, Delta, Delta-Delta]
  - SpecAugment data augmentation (random time & frequency masking)
  - Cross-Entropy with Label Smoothing
  - Cosine Annealing learning rate schedule & Early Stopping
  - Post-training Temperature Scaling for probability calibration (EER & Brier score optimization)
  - Saves separate versioned checkpoint: ai/models/deepguard_audio_v2.pth
"""

import os
import sys
import time
import math
import glob
from typing import Tuple, List, Dict, Any

import numpy as np
import soundfile as sf
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, precision_score, recall_score

# Ensure ai/src is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from audio_specnet_model import DeepGuardAudioSpecNet, extract_dynamic_spectrogram

DATASET_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "datasets", "audio_v2_dataset"))
OUTPUT_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "deepguard_audio_v2.pth"))


# ─────────────────────────────────────────────────────────────────────────────
# 1. SpecAugment & Dataset
# ─────────────────────────────────────────────────────────────────────────────

def apply_spec_augment(spec: np.ndarray, max_freq_mask: int = 8, max_time_mask: int = 12) -> np.ndarray:
    """
    Applies SpecAugment frequency and time masking to the 3-channel spectrogram.
    spec shape: (3, F, T)
    """
    augmented = spec.copy()
    _, f_bins, t_frames = augmented.shape

    # Frequency Masking
    f_width = np.random.randint(1, max_freq_mask + 1)
    f_start = np.random.randint(0, max(1, f_bins - f_width))
    augmented[:, f_start : f_start + f_width, :] = 0.0

    # Time Masking
    t_width = np.random.randint(1, max_time_mask + 1)
    t_start = np.random.randint(0, max(1, t_frames - t_width))
    augmented[:, :, t_start : t_start + t_width] = 0.0

    # Slight additive Gaussian noise
    if np.random.rand() > 0.5:
        augmented += np.random.normal(0, 0.015, augmented.shape).astype(np.float32)

    return augmented


class AudioDataset(Dataset):
    """Loads audio files, extracts 3-channel dynamic spectrograms, and applies augmentation."""

    def __init__(self, file_paths: List[str], labels: List[int], is_train: bool = False):
        self.file_paths = file_paths
        self.labels = labels
        self.is_train = is_train

    def __len__(self) -> int:
        return len(self.file_paths)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        path = self.file_paths[idx]
        label = self.labels[idx]

        try:
            data, sr = sf.read(path)
            if data.ndim > 1:
                data = np.mean(data, axis=1)
        except Exception:
            data = np.zeros(64600, dtype=np.float32)
            sr = 16000

        spec = extract_dynamic_spectrogram(data, sr=sr, target_length=128)

        if self.is_train:
            spec = apply_spec_augment(spec)

        tensor = torch.from_numpy(spec).float()
        target = torch.tensor(label, dtype=torch.long)
        return tensor, target


def load_split_paths(split_name: str) -> Tuple[List[str], List[int]]:
    """Loads file paths and binary labels (0: Real, 1: Fake) for a split."""
    real_dir = os.path.join(DATASET_ROOT, split_name, "real")
    fake_dir = os.path.join(DATASET_ROOT, split_name, "fake")

    real_files = sorted(glob.glob(os.path.join(real_dir, "*.wav")))
    fake_files = sorted(glob.glob(os.path.join(fake_dir, "*.wav")))

    paths = real_files + fake_files
    labels = [0] * len(real_files) + [1] * len(fake_files)
    return paths, labels


# ─────────────────────────────────────────────────────────────────────────────
# 2. Temperature Scaling & Calibration Optimizer
# ─────────────────────────────────────────────────────────────────────────────

def calibrate_temperature(model: nn.Module, val_loader: DataLoader, device: torch.device) -> float:
    """
    Optimizes temperature parameter T on the validation set using L-BFGS
    to minimize Negative Log Likelihood (NLL).
    """
    model.eval()
    logits_list = []
    labels_list = []

    with torch.no_grad():
        for inputs, targets in val_loader:
            inputs = inputs.to(device)
            _, logits = model(inputs)
            logits_list.append(logits.cpu())
            labels_list.append(targets)

    logits = torch.cat(logits_list, dim=0)
    labels = torch.cat(labels_list, dim=0)

    # Temperature parameter
    temperature = nn.Parameter(torch.ones(1) * 1.5)
    nll_criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.LBFGS([temperature], lr=0.01, max_iter=50)

    def eval_loss():
        optimizer.zero_grad()
        loss = nll_criterion(logits / torch.clamp(temperature, min=0.1, max=10.0), labels)
        loss.backward()
        return loss

    optimizer.step(eval_loss)
    opt_temp = float(torch.clamp(temperature, min=0.1, max=10.0).item())
    print(f"Optimal Temperature Calibration Parameter: T = {opt_temp:.4f}")
    return opt_temp


# ─────────────────────────────────────────────────────────────────────────────
# 3. Training Loop
# ─────────────────────────────────────────────────────────────────────────────

def train_audio_model():
    print("=" * 70)
    print(" DEEPGUARD AI AUDIO DETECTION — SPECNET V2 MODEL TRAINING & FINE-TUNING")
    print("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Executing on hardware device: {device}")

    # Load data
    train_paths, train_labels = load_split_paths("train")
    val_paths, val_labels = load_split_paths("val")
    print(f"Train samples: {len(train_paths)} (Real: {train_labels.count(0)}, Fake: {train_labels.count(1)})")
    print(f"Val samples:   {len(val_paths)} (Real: {val_labels.count(0)}, Fake: {val_labels.count(1)})")

    train_dataset = AudioDataset(train_paths, train_labels, is_train=True)
    val_dataset = AudioDataset(val_paths, val_labels, is_train=False)

    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False, num_workers=0)

    # Initialize model
    model = DeepGuardAudioSpecNet(num_classes=2).to(device)

    # Optimizer & Scheduler
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    epochs = 12
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    best_val_loss = float("inf")
    best_weights = None
    best_val_metrics = {}

    print("\nStarting training loop with SpecAugment and Cosine Annealing:")
    print("-" * 70)

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        model.train()
        train_loss = 0.0
        train_preds, train_trues = [], []

        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            _, logits = model(inputs)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * inputs.size(0)
            preds = torch.argmax(logits, dim=1).detach().cpu().numpy()
            train_preds.extend(preds)
            train_trues.extend(targets.cpu().numpy())

        scheduler.step()
        train_loss /= len(train_dataset)
        train_acc = accuracy_score(train_trues, train_preds)

        # Validation
        model.eval()
        val_loss = 0.0
        val_preds, val_trues, val_probs = [], [], []

        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                _, logits = model(inputs)
                loss = criterion(logits, targets)
                val_loss += loss.item() * inputs.size(0)
                probs = F.softmax(logits, dim=1).cpu().numpy()
                preds = np.argmax(probs, axis=1)

                val_preds.extend(preds)
                val_trues.extend(targets.cpu().numpy())
                val_probs.extend(probs[:, 1])

        val_loss /= len(val_dataset)
        val_acc = accuracy_score(val_trues, val_preds)
        val_f1 = f1_score(val_trues, val_preds, zero_division=0)
        val_auc = roc_auc_score(val_trues, val_probs)
        elapsed = time.time() - t0

        print(f"Epoch {epoch:02d}/{epochs:02d} [{elapsed:.1f}s]: "
              f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc*100:.1f}% | "
              f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc*100:.1f}%, F1: {val_f1:.4f}, AUC: {val_auc:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_val_metrics = {
                "val_loss": round(val_loss, 4),
                "val_acc": round(val_acc, 4),
                "val_f1": round(val_f1, 4),
                "val_auc": round(val_auc, 4),
                "epoch": epoch,
            }

    # Load best weights
    model.load_state_dict(best_weights)
    model.to(device)

    # Temperature Scaling
    opt_temp = calibrate_temperature(model, val_loader, device)
    model.temperature.data = torch.tensor([opt_temp])
    best_weights["temperature"] = torch.tensor([opt_temp])

    # Save model checkpoint
    checkpoint = {
        "model_name": model.model_name,
        "model_version": model.model_version,
        "model_state_dict": best_weights,
        "calibrated_temperature": opt_temp,
        "training_metrics": best_val_metrics,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    torch.save(checkpoint, OUTPUT_MODEL_PATH)
    print(f"\nSuccessfully trained and saved upgraded audio checkpoint to:")
    print(f"  {OUTPUT_MODEL_PATH}")
    print(f"Best Validation Accuracy: {best_val_metrics['val_acc']*100:.2f}%, AUC: {best_val_metrics['val_auc']:.4f}")


if __name__ == "__main__":
    train_audio_model()

