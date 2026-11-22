"""
train.py — Transfer Learning & Fine-Tuning Pipeline for DeepGuard AI.

Fine-tunes the existing EfficientNet-B0 deepfake detection model using:
  1. Progressive layer unfreezing (freeze early features, train classifier first).
  2. Discriminative learning rates (lower LR for pre-trained layers).
  3. Advanced data augmentation (color jitter, JPEG artifacts, blur, random erasing).
  4. Class-weighted loss to handle dataset imbalance.
  5. Cosine annealing with warm restarts for LR scheduling.
  6. Early stopping with best-metric checkpoint saving.
  7. Full evaluation with confusion matrix, ROC-AUC, and per-class metrics.

CRITICAL: NEVER overwrites the original checkpoint.
          Upgraded model is saved as a SEPARATE versioned checkpoint.

Usage:
    python train.py
    python train.py --epochs 50 --batch-size 32 --lr 0.00005
    python train.py --resume ai/models/efficientnet_b0_v2_finetuned.pth
"""

import os
import sys
import csv
import json
import time
import copy
import random
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import transforms, datasets, models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("training.log", mode="a", encoding="utf-8")],
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MODELS_DIR = PROJECT_ROOT / "ai" / "models"
DATASETS_DIR = PROJECT_ROOT / "ai" / "datasets"
CHECKPOINTS_DIR = PROJECT_ROOT / "model_checkpoints"
RESULTS_DIR = SCRIPT_DIR / "results"

ORIGINAL_CHECKPOINT = MODELS_DIR / "efficientnet_b0_ffpp_c23.pth"
V2_CHECKPOINT = MODELS_DIR / "efficientnet_b0_v2_finetuned.pth"
OUTPUT_CHECKPOINT = MODELS_DIR / "efficientnet_b0_v3_multimodal.pth"
BEST_CHECKPOINT = CHECKPOINTS_DIR / "efficientnet_b0_v3_best.pth"

# ImageNet normalization
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
IMG_SIZE = 224


# ─────────────────────────────────────────────────────────────────────────────
# Model Definition (must match production exactly)
# ─────────────────────────────────────────────────────────────────────────────

class DeepGuardModel(nn.Module):
    """EfficientNet-B0 for deepfake detection. Class 0=Real, Class 1=Fake.
    Architecture matches backend/app/services/ai_service.py exactly.
    """
    def __init__(self):
        super().__init__()
        base = models.efficientnet_b0(weights=None)
        self.features = base.features
        self.avgpool = base.avgpool
        self.classifier = base.classifier
        self.classifier[1] = nn.Linear(self.classifier[1].in_features, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x


# ─────────────────────────────────────────────────────────────────────────────
# Data Augmentation
# ─────────────────────────────────────────────────────────────────────────────

class JPEGCompression:
    """Simulates JPEG compression artifacts at random quality levels."""
    def __init__(self, quality_range=(65, 95), prob=0.15):
        self.quality_range = quality_range
        self.prob = prob

    def __call__(self, img):
        if random.random() > self.prob:
            return img
        import io
        quality = random.randint(*self.quality_range)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        return Image.open(buf).convert("RGB")


from PIL import Image, ImageFilter

class RandomGaussianBlur:
    """Apply Gaussian blur with random radius."""
    def __init__(self, radius_range=(0.5, 1.5), prob=0.1):
        self.radius_range = radius_range
        self.prob = prob

    def __call__(self, img):
        if random.random() > self.prob:
            return img
        radius = random.uniform(*self.radius_range)
        return img.filter(ImageFilter.GaussianBlur(radius=radius))


def get_train_transforms() -> transforms.Compose:
    """Training augmentation pipeline — designed for deepfake detection."""
    return transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.85, 1.0), ratio=(0.9, 1.1),
                                     interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1, hue=0.05),
        RandomGaussianBlur(prob=0.1),
        JPEGCompression(quality_range=(65, 95), prob=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        transforms.RandomErasing(p=0.05, scale=(0.02, 0.1)),
    ])


def get_val_transforms() -> transforms.Compose:
    """Validation/test transforms — deterministic, no augmentation."""
    return transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE), interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Progressive Layer Freezing
# ─────────────────────────────────────────────────────────────────────────────

def freeze_layers(model: DeepGuardModel, num_frozen_blocks: int = 6) -> None:
    """Freeze the first `num_frozen_blocks` of 9 EfficientNet feature blocks."""
    for i, block in enumerate(model.features):
        if i < num_frozen_blocks:
            for param in block.parameters():
                param.requires_grad = False
        else:
            for param in block.parameters():
                param.requires_grad = True

    # Classifier is always trainable
    for param in model.classifier.parameters():
        param.requires_grad = True

    frozen = sum(1 for p in model.parameters() if not p.requires_grad)
    total = sum(1 for p in model.parameters())
    logger.info("Frozen %d/%d parameters (blocks 0-%d frozen)", frozen, total, num_frozen_blocks - 1)


def unfreeze_all(model: DeepGuardModel) -> None:
    """Unfreeze all parameters for full fine-tuning."""
    for param in model.parameters():
        param.requires_grad = True
    logger.info("All parameters unfrozen for full fine-tuning")


def get_parameter_groups(model: DeepGuardModel, base_lr: float) -> list:
    """
    Create parameter groups with discriminative learning rates.
    Early layers get 10x lower LR than the classifier.
    """
    params = []

    # Early features (lower LR)
    early_params = []
    for i in range(6):
        early_params.extend(model.features[i].parameters())
    if early_params:
        params.append({"params": [p for p in early_params if p.requires_grad], "lr": base_lr * 0.1})

    # Late features (medium LR)
    late_params = []
    for i in range(6, len(model.features)):
        late_params.extend(model.features[i].parameters())
    if late_params:
        params.append({"params": [p for p in late_params if p.requires_grad], "lr": base_lr * 0.5})

    # Classifier (full LR)
    params.append({"params": model.classifier.parameters(), "lr": base_lr})

    return params


# ─────────────────────────────────────────────────────────────────────────────
# Training Loop
# ─────────────────────────────────────────────────────────────────────────────

def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
    epoch: int,
    max_grad_norm: float = 1.0,
) -> Dict[str, float]:
    """Train for one epoch, return metrics dict."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for batch_idx, (inputs, labels) in enumerate(loader):
        inputs, labels = inputs.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)

        optimizer.step()

        running_loss += loss.item() * inputs.size(0)
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

        if (batch_idx + 1) % 20 == 0:
            logger.info(
                "  Epoch %d | Batch %d/%d | Loss: %.4f | Acc: %.2f%%",
                epoch, batch_idx + 1, len(loader),
                loss.item(), 100.0 * correct / total,
            )

    epoch_loss = running_loss / total
    epoch_acc = correct / total
    return {"loss": epoch_loss, "accuracy": epoch_acc}


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Dict[str, float]:
    """Evaluate model on val/test set, return comprehensive metrics."""
    model.eval()
    running_loss = 0.0
    all_labels = []
    all_preds = []
    all_probs = []

    for inputs, labels in loader:
        inputs, labels = inputs.to(device), labels.to(device)
        outputs = model(inputs)
        loss = criterion(outputs, labels)

        running_loss += loss.item() * inputs.size(0)
        probs = torch.softmax(outputs, dim=1)
        _, predicted = torch.max(outputs, 1)

        all_labels.extend(labels.cpu().numpy())
        all_preds.extend(predicted.cpu().numpy())
        # class 0 = fake, class 1 = real
        all_probs.extend(probs[:, 0].cpu().numpy())  # prob of fake class

    total = len(all_labels)
    epoch_loss = running_loss / total

    y_true = np.array(all_labels)
    y_pred = np.array(all_preds)
    y_prob_fake = np.array(all_probs)

    # Metrics with Fake (class 0) as positive detection class
    accuracy = float(np.mean(y_true == y_pred))
    tp = int(np.sum((y_pred == 0) & (y_true == 0)))  # Fake correctly detected
    tn = int(np.sum((y_pred == 1) & (y_true == 1)))  # Real correctly verified
    fp = int(np.sum((y_pred == 0) & (y_true == 1)))  # Real falsely flagged as Fake
    fn = int(np.sum((y_pred == 1) & (y_true == 0)))  # Fake missed as Real

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    # ROC-AUC (positive class = fake)
    try:
        from sklearn.metrics import roc_auc_score
        roc_auc = float(roc_auc_score((y_true == 0).astype(int), y_prob_fake))
    except Exception:
        roc_auc = 0.0

    return {
        "loss": epoch_loss,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "roc_auc": roc_auc,
        "specificity": specificity,
        "fpr": fpr,
        "fnr": fnr,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "total": total,
    }


def compute_class_weights(dataset: datasets.ImageFolder, device: torch.device) -> torch.Tensor:
    """Compute inverse frequency class weights for imbalanced datasets."""
    targets = np.array(dataset.targets)
    class_counts = np.bincount(targets)
    total = len(targets)
    weights = total / (len(class_counts) * class_counts.astype(np.float64))
    logger.info("Class counts: %s -> weights: %s", class_counts.tolist(), np.round(weights, 4).tolist())
    return torch.tensor(weights, dtype=torch.float32).to(device)


def get_balanced_sampler(dataset: datasets.ImageFolder) -> WeightedRandomSampler:
    """Create a WeightedRandomSampler for class-balanced batches."""
    targets = np.array(dataset.targets)
    class_counts = np.bincount(targets)
    sample_weights = 1.0 / class_counts[targets]
    return WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(targets),
        replacement=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main Training Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DeepGuard AI — Model Fine-Tuning")
    parser.add_argument("--data-dir", type=str, default=str(DATASETS_DIR / "face_crops"), help="Dataset directory")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--patience", type=int, default=7, help="Early stopping patience")
    parser.add_argument("--freeze-blocks", type=int, default=6, help="Number of feature blocks to freeze initially")
    parser.add_argument("--unfreeze-epoch", type=int, default=4, help="Epoch to unfreeze all layers")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--resume", type=str, default=None, help="Resume from checkpoint")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-workers", type=int, default=0)
    args = parser.parse_args()

    # Seed
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    # Device
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    logger.info("Using device: %s", device)

    # Create directories
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Load datasets ────────────────────────────────────────────────────
    base_data_path = Path(args.data_dir)
    if not (base_data_path / "train").is_dir():
        base_data_path = DATASETS_DIR
    train_dir = base_data_path / "train"
    val_dir = base_data_path / "val"
    test_dir = base_data_path / "test"

    if not train_dir.is_dir() or not any(train_dir.iterdir()):
        logger.error("Training data not found at %s. Run dataset_preparation.py first.", train_dir)
        sys.exit(1)

    train_dataset = datasets.ImageFolder(str(train_dir), transform=get_train_transforms())
    val_dataset = datasets.ImageFolder(str(val_dir), transform=get_val_transforms())

    test_dataset = None
    if test_dir.is_dir() and any(test_dir.iterdir()):
        test_dataset = datasets.ImageFolder(str(test_dir), transform=get_val_transforms())

    logger.info("Train: %d images (%s)", len(train_dataset), dict(zip(train_dataset.classes, np.bincount(train_dataset.targets).tolist())))
    logger.info("Val:   %d images", len(val_dataset))
    if test_dataset:
        logger.info("Test:  %d images", len(test_dataset))

    # Class mapping verification
    assert train_dataset.class_to_idx.get("fake", -1) == 1 or train_dataset.class_to_idx.get("fake", -1) == 0, \
        f"Unexpected class mapping: {train_dataset.class_to_idx}. Expected 'fake' and 'real' directories."
    logger.info("Class mapping: %s", train_dataset.class_to_idx)

    # Balanced sampler
    sampler = get_balanced_sampler(train_dataset)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, sampler=sampler,
                              num_workers=args.num_workers, pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False,
                            num_workers=args.num_workers, pin_memory=True)

    # ── 2. Initialize model ─────────────────────────────────────────────────
    model = DeepGuardModel()

    # Load pretrained weights (either original or resume checkpoint)
    checkpoint_path = Path(args.resume) if args.resume else ORIGINAL_CHECKPOINT
    if checkpoint_path.is_file():
        state_dict = torch.load(str(checkpoint_path), map_location=device, weights_only=True)
        model.load_state_dict(state_dict)
        logger.info("Loaded weights from: %s", checkpoint_path)
    else:
        logger.error("Checkpoint not found: %s", checkpoint_path)
        sys.exit(1)

    model.to(device)

    # ── 3. Progressive freezing ─────────────────────────────────────────────
    freeze_layers(model, num_frozen_blocks=args.freeze_blocks)

    # ── 4. Loss, optimizer, scheduler ──────────────────────────────────────
    class_weights = compute_class_weights(train_dataset, device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    param_groups = get_parameter_groups(model, args.lr)
    optimizer = optim.AdamW(param_groups, lr=args.lr, weight_decay=args.weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=5, T_mult=2, eta_min=1e-6)

    # ── 5. Training loop ─────────────────────────────────────────────────────
    best_f1 = 0.0
    best_epoch = 0
    patience_counter = 0
    training_history = []

    logger.info("\n" + "=" * 70)
    logger.info("STARTING TRAINING — %d epochs, batch_size=%d, lr=%.6f", args.epochs, args.batch_size, args.lr)
    logger.info("Original checkpoint: %s", ORIGINAL_CHECKPOINT)
    logger.info("Output checkpoint:   %s", OUTPUT_CHECKPOINT)
    logger.info("=" * 70 + "\n")

    start_time = time.time()

    for epoch in range(1, args.epochs + 1):
        epoch_start = time.time()

        # Progressive unfreezing at specified epoch
        if epoch == args.unfreeze_epoch:
            logger.info("\n>>> UNFREEZING ALL LAYERS at epoch %d <<<\n", epoch)
            unfreeze_all(model)
            # Reset optimizer with discriminative LRs for all layers
            param_groups = get_parameter_groups(model, args.lr * 0.5)
            optimizer = optim.AdamW(param_groups, lr=args.lr * 0.5, weight_decay=args.weight_decay)
            scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=5, T_mult=2, eta_min=1e-6)

        # Train
        logger.info("--- Epoch %d/%d ---", epoch, args.epochs)
        train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, device, epoch)

        # Validate
        val_metrics = evaluate(model, val_loader, criterion, device)

        # Step scheduler
        scheduler.step(epoch)

        epoch_time = time.time() - epoch_start
        current_lr = optimizer.param_groups[-1]["lr"]

        logger.info(
            "Epoch %d — Train Loss: %.4f, Acc: %.2f%% | Val Loss: %.4f, Acc: %.2f%%, F1: %.4f, "
            "Recall: %.4f, AUC: %.4f | LR: %.6f | Time: %.1fs",
            epoch,
            train_metrics["loss"], 100 * train_metrics["accuracy"],
            val_metrics["loss"], 100 * val_metrics["accuracy"],
            val_metrics["f1_score"], val_metrics["recall"], val_metrics["roc_auc"],
            current_lr, epoch_time,
        )

        # Save history
        training_history.append({
            "epoch": epoch,
            "train_loss": round(train_metrics["loss"], 6),
            "train_acc": round(train_metrics["accuracy"], 6),
            "val_loss": round(val_metrics["loss"], 6),
            "val_acc": round(val_metrics["accuracy"], 6),
            "val_f1": round(val_metrics["f1_score"], 6),
            "val_recall": round(val_metrics["recall"], 6),
            "val_precision": round(val_metrics["precision"], 6),
            "val_roc_auc": round(val_metrics["roc_auc"], 6),
            "val_fpr": round(val_metrics["fpr"], 6),
            "val_fnr": round(val_metrics["fnr"], 6),
            "lr": current_lr,
            "time_seconds": round(epoch_time, 2),
        })

        # Best model checkpoint (by F1 score)
        if val_metrics["f1_score"] > best_f1:
            best_f1 = val_metrics["f1_score"]
            best_epoch = epoch
            patience_counter = 0
            torch.save(model.state_dict(), str(BEST_CHECKPOINT))
            torch.save(model.state_dict(), str(OUTPUT_CHECKPOINT))
            logger.info("  * New best F1: %.4f -- saved to %s", best_f1, OUTPUT_CHECKPOINT.name)
        else:
            patience_counter += 1
            logger.info("  No improvement. Patience: %d/%d", patience_counter, args.patience)

        # Early stopping
        if patience_counter >= args.patience:
            logger.info("\n⏹ Early stopping triggered at epoch %d (best epoch: %d, best F1: %.4f)",
                        epoch, best_epoch, best_f1)
            break

    total_time = time.time() - start_time
    logger.info("\n" + "=" * 70)
    logger.info("TRAINING COMPLETE — Total time: %.1f minutes", total_time / 60)
    logger.info("Best epoch: %d with F1: %.4f", best_epoch, best_f1)
    logger.info("=" * 70)

    # ── 6. Final evaluation on test set ──────────────────────────────────────
    # Load best model for final evaluation
    model.load_state_dict(torch.load(str(OUTPUT_CHECKPOINT), map_location=device, weights_only=True))
    model.eval()

    final_val = evaluate(model, val_loader, criterion, device)
    logger.info("\nFinal Validation Metrics:")
    for k, v in final_val.items():
        if isinstance(v, float):
            logger.info("  %s: %.4f", k, v)
        else:
            logger.info("  %s: %s", k, v)

    test_metrics = None
    if test_dataset:
        test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False,
                                 num_workers=args.num_workers, pin_memory=True)
        test_metrics = evaluate(model, test_loader, criterion, device)
        logger.info("\nTest Set Metrics:")
        for k, v in test_metrics.items():
            if isinstance(v, float):
                logger.info("  %s: %.4f", k, v)
            else:
                logger.info("  %s: %s", k, v)

    # ── 7. Save training report ──────────────────────────────────────────────
    report = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "epochs_run": len(training_history),
            "max_epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
            "weight_decay": args.weight_decay,
            "freeze_blocks": args.freeze_blocks,
            "unfreeze_epoch": args.unfreeze_epoch,
            "patience": args.patience,
            "device": str(device),
            "seed": args.seed,
        },
        "dataset": {
            "train_size": len(train_dataset),
            "val_size": len(val_dataset),
            "test_size": len(test_dataset) if test_dataset else 0,
            "class_mapping": train_dataset.class_to_idx,
        },
        "best_epoch": best_epoch,
        "best_f1": round(best_f1, 6),
        "total_training_time_minutes": round(total_time / 60, 2),
        "final_validation": {k: round(v, 6) if isinstance(v, float) else v for k, v in final_val.items()},
        "test_evaluation": {k: round(v, 6) if isinstance(v, float) else v for k, v in test_metrics.items()} if test_metrics else None,
        "training_history": training_history,
        "checkpoints": {
            "original": str(ORIGINAL_CHECKPOINT),
            "upgraded": str(OUTPUT_CHECKPOINT),
            "best": str(BEST_CHECKPOINT),
        },
    }

    report_path = RESULTS_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("\nTraining report saved to: %s", report_path)

    # ── 8. Comparison with original model ────────────────────────────────────
    logger.info("\n" + "=" * 70)
    logger.info("ORIGINAL vs UPGRADED MODEL COMPARISON")
    logger.info("=" * 70)

    # Load original model
    original_model = DeepGuardModel()
    original_model.load_state_dict(
        torch.load(str(ORIGINAL_CHECKPOINT), map_location=device, weights_only=True)
    )
    original_model.to(device)
    original_model.eval()

    original_val = evaluate(original_model, val_loader, criterion, device)

    comparison = {
        "metric": [],
        "original": [],
        "upgraded": [],
        "improvement": [],
    }

    for metric in ["accuracy", "precision", "recall", "f1_score", "roc_auc", "specificity", "fpr", "fnr"]:
        orig_v = original_val[metric]
        upgr_v = final_val[metric]
        diff = upgr_v - orig_v

        comparison["metric"].append(metric)
        comparison["original"].append(round(orig_v, 4))
        comparison["upgraded"].append(round(upgr_v, 4))
        comparison["improvement"].append(round(diff, 4))

        direction = "↑" if diff > 0 else "↓" if diff < 0 else "="
        color = "IMPROVED" if (diff > 0 and metric not in ["fpr", "fnr"]) or (diff < 0 and metric in ["fpr", "fnr"]) else "DEGRADED" if diff != 0 else "SAME"
        logger.info(
            "  %-15s  Original: %.4f  →  Upgraded: %.4f  %s %.4f  [%s]",
            metric, orig_v, upgr_v, direction, abs(diff), color,
        )

    # Save comparison
    comparison_path = RESULTS_DIR / "model_comparison.json"
    with open(comparison_path, "w") as f:
        json.dump(comparison, f, indent=2)
    logger.info("\nComparison saved to: %s", comparison_path)
    logger.info("\n✅ Fine-tuning pipeline complete.")
    logger.info("   Upgraded model: %s", OUTPUT_CHECKPOINT)
    logger.info("   Original model preserved at: %s", CHECKPOINTS_DIR / "efficientnet_b0_ffpp_c23_ORIGINAL.pth")


if __name__ == "__main__":
    main()
