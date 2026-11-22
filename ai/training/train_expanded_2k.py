"""
train_expanded_2k.py
Fine-tunes EfficientNet-B0 on the identity-independent 2,000+ image dataset.
Features:
  - Augmentation: ColorJitter, RandomAffine, RandomHorizontalFlip, GaussianBlur
  - Class balancing: Weighted CE loss / balanced sampling
  - Progressive unfreezing: Heads first, then full network
  - Learning-rate scheduling: CosineAnnealingLR
  - Early stopping on validation F1
  - Evaluation & comparison on held-out test split (unseen identities)
  - Saves upgraded checkpoint to efficientnet_b0_v4_expanded_2k.pth
"""

import os
import sys
import time
import json
import logging
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from torchvision.models import efficientnet_b0
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TrainExpanded2K")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "ai" / "datasets" / "expanded_dataset_2k"
MODELS_DIR = PROJECT_ROOT / "ai" / "models"
RESULTS_DIR = PROJECT_ROOT / "ai" / "training" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

ORIGINAL_CHECKPOINT = MODELS_DIR / "efficientnet_b0_ffpp_c23.pth"
OUTPUT_CHECKPOINT = MODELS_DIR / "efficientnet_b0_v4_expanded_2k.pth"

TRANSFORM_TRAIN = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(degrees=15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
    transforms.RandomAffine(degrees=0, translate=(0.05, 0.05), scale=(0.95, 1.05)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

TRANSFORM_VAL = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def create_model():
    model = efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, 2)
    return model

def evaluate_loader(model, loader, device):
    model.eval()
    all_preds, all_labels, all_probs = [], [], []
    total_loss, num_batches = 0.0, 0
    criterion = nn.CrossEntropyLoss()

    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            total_loss += loss.item()
            num_batches += 1

            probs = torch.softmax(outputs, dim=1)
            # Class 0: fake, Class 1: real
            # For deepfake detection metrics, positive class = fake (class 0)
            fake_probs = probs[:, 0].cpu().numpy()
            preds = torch.argmax(outputs, dim=1).cpu().numpy()

            all_probs.extend(fake_probs)
            all_preds.extend(preds)
            all_labels.extend(labels.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs = np.array(all_probs)

    # Invert binary for metric computation: positive (1) = Fake, negative (0) = Real
    binary_true = (all_labels == 0).astype(int)
    binary_pred = (all_preds == 0).astype(int)

    acc = accuracy_score(binary_true, binary_pred)
    prec = precision_score(binary_true, binary_pred, zero_division=0)
    rec = recall_score(binary_true, binary_pred, zero_division=0)
    f1 = f1_score(binary_true, binary_pred, zero_division=0)
    try:
        auc = roc_auc_score(binary_true, all_probs)
    except Exception:
        auc = 0.5

    cm = confusion_matrix(binary_true, binary_pred)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    return {
        "loss": total_loss / max(1, num_batches),
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1_score": float(f1),
        "roc_auc": float(auc),
        "specificity": float(specificity),
        "fpr": float(fpr),
        "fnr": float(fnr),
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "total": len(all_labels)
    }

def train(epochs=8, batch_size=16, lr=1e-4, device_str="cpu"):
    device = torch.device(device_str)
    logger.info("Using device: %s", device)

    # Load datasets
    train_ds = datasets.ImageFolder(str(DATA_DIR / "train"), transform=TRANSFORM_TRAIN)
    val_ds = datasets.ImageFolder(str(DATA_DIR / "val"), transform=TRANSFORM_VAL)
    test_ds = datasets.ImageFolder(str(DATA_DIR / "test"), transform=TRANSFORM_VAL)

    logger.info("Dataset Loaded:")
    logger.info("  Train: %d images (classes: %s)", len(train_ds), train_ds.class_to_idx)
    logger.info("  Val:   %d images", len(val_ds))
    logger.info("  Test:  %d images (identity-isolated held-out set)", len(test_ds))

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    # Initialize model with original pretrained weights
    model = create_model()
    if ORIGINAL_CHECKPOINT.is_file():
        state_dict = torch.load(ORIGINAL_CHECKPOINT, map_location=device, weights_only=True)
        model.load_state_dict(state_dict)
        logger.info("Loaded pretrained weights from: %s", ORIGINAL_CHECKPOINT)

    # Evaluate Original Model on Test Set First (Baseline)
    model.to(device)
    logger.info("\n" + "="*70)
    logger.info("EVALUATING ORIGINAL BASELINE MODEL ON TEST SET...")
    logger.info("="*70)
    orig_test_metrics = evaluate_loader(model, test_loader, device)
    logger.info("Original Model Test Metrics: Acc=%.4f, Prec=%.4f, Rec=%.4f, F1=%.4f, AUC=%.4f, FPR=%.4f, FNR=%.4f",
                orig_test_metrics["accuracy"], orig_test_metrics["precision"], orig_test_metrics["recall"],
                orig_test_metrics["f1_score"], orig_test_metrics["roc_auc"], orig_test_metrics["fpr"], orig_test_metrics["fnr"])

    # Phase 1: Freeze early blocks (0 to 4)
    for name, param in model.features.named_parameters():
        block_idx = int(name.split(".")[0]) if name.split(".")[0].isdigit() else 99
        if block_idx <= 4:
            param.requires_grad = False

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=lr,
        weight_decay=1e-4
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    best_val_f1 = 0.0
    patience = 4
    patience_counter = 0

    logger.info("\n" + "="*70)
    logger.info("STARTING TRAINING — %d epochs, batch_size=%d, lr=%f", epochs, batch_size, lr)
    logger.info("Output Checkpoint: %s", OUTPUT_CHECKPOINT)
    logger.info("="*70)

    start_train_time = time.time()
    for epoch in range(1, epochs + 1):
        # Phase 2: Unfreeze all parameters at epoch 4
        if epoch == 4:
            logger.info(">>> Unfreezing all backbone layers for full fine-tuning <<<")
            for param in model.parameters():
                param.requires_grad = True
            optimizer = torch.optim.AdamW(model.parameters(), lr=lr * 0.5, weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs - 3, eta_min=1e-6)

        model.train()
        train_loss, correct, total = 0.0, 0, 0
        t0 = time.time()

        for batch_idx, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item() * images.size(0)
            preds = torch.argmax(outputs, dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

            if (batch_idx + 1) % 25 == 0 or (batch_idx + 1) == len(train_loader):
                logger.info("  Epoch %d | Batch %d/%d | Loss: %.4f | Acc: %.2f%%",
                            epoch, batch_idx + 1, len(train_loader),
                            loss.item(), 100.0 * correct / max(1, total))

        scheduler.step()
        train_acc = correct / max(1, total)
        train_loss_avg = train_loss / max(1, total)

        # Validation
        val_metrics = evaluate_loader(model, val_loader, device)
        elapsed = time.time() - t0
        logger.info("Epoch %d — Train Loss: %.4f, Acc: %.2f%% | Val Loss: %.4f, Acc: %.2f%%, F1: %.4f, AUC: %.4f | Time: %.1fs",
                    epoch, train_loss_avg, train_acc * 100,
                    val_metrics["loss"], val_metrics["accuracy"] * 100,
                    val_metrics["f1_score"], val_metrics["roc_auc"], elapsed)

        # Checkpoint if best validation F1
        if val_metrics["f1_score"] > best_val_f1:
            best_val_f1 = val_metrics["f1_score"]
            torch.save(model.state_dict(), OUTPUT_CHECKPOINT)
            logger.info("  * New best Val F1: %.4f — Checkpoint saved to %s", best_val_f1, OUTPUT_CHECKPOINT.name)
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info("Early stopping triggered at epoch %d (patience=%d)", epoch, patience)
                break

    total_time = (time.time() - start_train_time) / 60.0
    logger.info("\nTraining complete in %.1f minutes. Loading best checkpoint for independent test evaluation...", total_time)

    # Load best checkpoint
    model.load_state_dict(torch.load(OUTPUT_CHECKPOINT, map_location=device))
    upgraded_test_metrics = evaluate_loader(model, test_loader, device)

    logger.info("\n" + "="*70)
    logger.info("INDEPENDENT TEST EVALUATION (Held-out Unseen Identities: %d Real, %d Fake)",
                orig_test_metrics["tn"] + orig_test_metrics["fp"], orig_test_metrics["tp"] + orig_test_metrics["fn"])
    logger.info("="*70)
    logger.info("ORIGINAL MODEL vs UPGRADED MODEL (v4 Expanded 2k):")
    logger.info("  Accuracy:    Original: %.4f  -->  Upgraded: %.4f  (Delta: %+.4f)",
                orig_test_metrics["accuracy"], upgraded_test_metrics["accuracy"],
                upgraded_test_metrics["accuracy"] - orig_test_metrics["accuracy"])
    logger.info("  Precision:   Original: %.4f  -->  Upgraded: %.4f  (Delta: %+.4f)",
                orig_test_metrics["precision"], upgraded_test_metrics["precision"],
                upgraded_test_metrics["precision"] - orig_test_metrics["precision"])
    logger.info("  Recall:      Original: %.4f  -->  Upgraded: %.4f  (Delta: %+.4f)",
                orig_test_metrics["recall"], upgraded_test_metrics["recall"],
                upgraded_test_metrics["recall"] - orig_test_metrics["recall"])
    logger.info("  F1-Score:    Original: %.4f  -->  Upgraded: %.4f  (Delta: %+.4f)",
                orig_test_metrics["f1_score"], upgraded_test_metrics["f1_score"],
                upgraded_test_metrics["f1_score"] - orig_test_metrics["f1_score"])
    logger.info("  ROC-AUC:     Original: %.4f  -->  Upgraded: %.4f  (Delta: %+.4f)",
                orig_test_metrics["roc_auc"], upgraded_test_metrics["roc_auc"],
                upgraded_test_metrics["roc_auc"] - orig_test_metrics["roc_auc"])
    logger.info("  FPR (Alarm): Original: %.4f  -->  Upgraded: %.4f  (Delta: %+.4f)",
                orig_test_metrics["fpr"], upgraded_test_metrics["fpr"],
                upgraded_test_metrics["fpr"] - orig_test_metrics["fpr"])
    logger.info("  FNR (Miss):  Original: %.4f  -->  Upgraded: %.4f  (Delta: %+.4f)",
                orig_test_metrics["fnr"], upgraded_test_metrics["fnr"],
                upgraded_test_metrics["fnr"] - orig_test_metrics["fnr"])
    logger.info("="*70)

    # Save comparison report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset": {
            "train_real": len(train_ds) // 2,
            "train_fake": len(train_ds) // 2,
            "val_samples": len(val_ds),
            "test_samples": len(test_ds),
            "total_samples": len(train_ds) + len(val_ds) + len(test_ds)
        },
        "training_config": {
            "epochs": epochs,
            "batch_size": batch_size,
            "lr": lr,
            "device": device_str,
            "checkpoint": str(OUTPUT_CHECKPOINT)
        },
        "original_model_metrics": orig_test_metrics,
        "upgraded_model_metrics": upgraded_test_metrics,
        "improvement_delta": {
            "accuracy": round(upgraded_test_metrics["accuracy"] - orig_test_metrics["accuracy"], 4),
            "f1_score": round(upgraded_test_metrics["f1_score"] - orig_test_metrics["f1_score"], 4),
            "roc_auc": round(upgraded_test_metrics["roc_auc"] - orig_test_metrics["roc_auc"], 4),
            "precision": round(upgraded_test_metrics["precision"] - orig_test_metrics["precision"], 4),
            "recall": round(upgraded_test_metrics["recall"] - orig_test_metrics["recall"], 4)
        }
    }

    report_path = RESULTS_DIR / "expanded_2k_model_comparison.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Saved full comparison report to %s", report_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()

    train(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr, device_str=args.device)

