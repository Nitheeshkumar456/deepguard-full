"""
train_video_models.py
Trains and evaluates:
1. EfficientNet-B0 v5 Video-Optimized Frame-Level Classifier (ai/models/efficientnet_b0_v5_video.pth)
2. DeepGuard BiGRU Temporal Consistency Model (ai/models/deepguard_temporal_v5.pth)
Evaluates frame-level and video-level performance independently on strictly held-out test splits.
"""

import os
import json
import time
import copy
from pathlib import Path
from collections import defaultdict
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import efficientnet_b0
from PIL import Image
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)

DEVICE = torch.device("cpu")
torch.manual_seed(42)
np.random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Models
# ─────────────────────────────────────────────────────────────────────────────

class DeepGuardModel(nn.Module):
    def __init__(self):
        super().__init__()
        base = efficientnet_b0(weights=None)
        self.features = base.features
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        in_features = base.classifier[1].in_features
        self.classifier = nn.Sequential(
            nn.Dropout(p=0.2, inplace=True),
            nn.Linear(in_features, 2)
        )

    def extract_features(self, x):
        feat = self.features(x)
        feat = self.avgpool(feat)
        return torch.flatten(feat, 1)

    def forward(self, x):
        feat = self.extract_features(x)
        return self.classifier(feat)


class TemporalSelfAttention(nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        self.proj = nn.Linear(hidden_dim, 64)
        self.query = nn.Linear(64, 1, bias=False)

    def forward(self, x):
        # x: (B, T, hidden_dim)
        score = torch.tanh(self.proj(x)) # (B, T, 64)
        score = self.query(score).squeeze(-1) # (B, T)
        weights = F.softmax(score, dim=-1).unsqueeze(-1) # (B, T, 1)
        context = torch.sum(x * weights, dim=1) # (B, hidden_dim)
        return context, weights.squeeze(-1)


class DeepGuardTemporalModel(nn.Module):
    """
    Bi-directional GRU with Temporal Self-Attention for detecting inter-frame
    flickering, face-swap blending inconsistencies, and temporal jitter.
    """
    def __init__(self, feat_dim=1280, hidden_dim=64):
        super().__init__()
        # Input features: current frame feature (1280) + temporal difference (1280) = 2560
        self.input_proj = nn.Sequential(
            nn.Linear(feat_dim * 2, 128),
            nn.LayerNorm(128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3)
        )
        self.bigru = nn.GRU(
            input_size=128,
            hidden_size=hidden_dim,
            num_layers=1,
            batch_first=True,
            bidirectional=True
        )
        self.attention = TemporalSelfAttention(hidden_dim * 2)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(32, 2) # [0: Authentic, 1: Synthetic]
        )

    def forward(self, seq_feats):
        # seq_feats: (B, T, feat_dim)
        B, T, D = seq_feats.shape
        # Compute forward temporal differences: d_t = f_t - f_{t-1}
        diffs = torch.zeros_like(seq_feats)
        diffs[:, 1:, :] = seq_feats[:, 1:, :] - seq_feats[:, :-1, :]
        combined = torch.cat([seq_feats, diffs], dim=-1) # (B, T, 2*D)

        x = self.input_proj(combined) # (B, T, 128)
        gru_out, _ = self.bigru(x) # (B, T, 128)
        context, attn_weights = self.attention(gru_out) # (B, 128), (B, T)
        logits = self.classifier(context) # (B, 2)
        return logits, attn_weights

# ─────────────────────────────────────────────────────────────────────────────
# 2. Datasets
# ─────────────────────────────────────────────────────────────────────────────

class FrameDataset(Dataset):
    def __init__(self, frame_items, base_dir, transform=None):
        self.items = frame_items
        self.base_dir = Path(base_dir)
        self.transform = transform

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        item = self.items[idx]
        img_path = self.base_dir / item["rel_path"]
        img = Image.open(img_path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        # Class mapping: 0=Fake, 1=Real (matching existing DeepGuard checkpoint)
        label = item["class"]
        return img, label, item["video_name"], item["frame_order"]


def get_transforms():
    train_transform = transforms.Compose([
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    eval_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    return train_transform, eval_transform

# ─────────────────────────────────────────────────────────────────────────────
# 3. Training & Evaluation Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def train_frame_model(train_loader, val_loader, class_weights, epochs=3):
    print("\n=======================================================")
    print("PHASE 1: Training Video-Optimized Frame Model (v5)")
    print("=======================================================")
    model = DeepGuardModel().to(DEVICE)

    v5_path = Path("ai/models/efficientnet_b0_v5_video.pth")
    if v5_path.exists():
        print(f"Loading existing trained v5 model from: {v5_path}")
        state = torch.load(v5_path, map_location=DEVICE)
        if "model_state_dict" in state:
            state = state["model_state_dict"]
        model.load_state_dict(state, strict=False)
        return model

    # Initialize from upgraded v4 checkpoint
    v4_path = Path("ai/models/efficientnet_b0_v4_expanded_2k.pth")
    if not v4_path.exists():
        v4_path = Path("ai/models/efficientnet_b0_ffpp_c23.pth")
    print(f"Loading base weights from: {v4_path}")
    state = torch.load(v4_path, map_location=DEVICE)
    if "model_state_dict" in state:
        state = state["model_state_dict"]
    model.load_state_dict(state, strict=False)

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(DEVICE))
    best_acc = 0.0
    best_weights = copy.deepcopy(model.state_dict())

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        t0 = time.time()

        for imgs, labels, _, _ in train_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            logits = model(imgs)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * imgs.size(0)
            preds = logits.argmax(dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        train_loss = total_loss / max(1, total)
        train_acc = correct / max(1, total)

        # Validation
        model.eval()
        v_correct, v_total = 0, 0
        with torch.no_grad():
            for imgs, labels, _, _ in val_loader:
                imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
                logits = model(imgs)
                preds = logits.argmax(dim=1)
                v_correct += (preds == labels).sum().item()
                v_total += labels.size(0)

        val_acc = v_correct / max(1, v_total)
        elapsed = time.time() - t0
        print(f"Epoch {epoch}/{epochs} ({elapsed:.1f}s) | Train Loss: {train_loss:.4f}, Acc: {train_acc:.4f} | Val Acc: {val_acc:.4f}")

        if val_acc >= best_acc:
            best_acc = val_acc
            best_weights = copy.deepcopy(model.state_dict())

    model.load_state_dict(best_weights)
    out_path = Path("ai/models/efficientnet_b0_v5_video.pth")
    torch.save({
        "model_state_dict": model.state_dict(),
        "model_version": "5.0.0",
        "model_name": "EfficientNet-B0-v5-Video",
        "best_val_acc": best_acc
    }, out_path)
    print(f"--> Saved v5 Frame Model to {out_path} (Best Val Acc: {best_acc:.4f})")
    return model


def extract_video_sequences(model, frame_items, base_dir, transform):
    """Extracts sequential 1280-dim feature vectors grouped by video."""
    model.eval()
    dataset = FrameDataset(frame_items, base_dir, transform=transform)
    loader = DataLoader(dataset, batch_size=32, shuffle=False)

    video_feats = defaultdict(list)
    video_labels = {}

    with torch.no_grad():
        for imgs, labels, vid_names, orders in loader:
            imgs = imgs.to(DEVICE)
            feats = model.extract_features(imgs) # (B, 1280)
            feats_np = feats.cpu().numpy()
            for feat, lbl, vname, order in zip(feats_np, labels.numpy(), vid_names, orders.numpy()):
                video_feats[vname].append((order, feat))
                video_labels[vname] = lbl

    sequences = []
    seq_labels = []
    seq_names = []

    for vname, feat_list in video_feats.items():
        # Sort by frame order
        feat_list.sort(key=lambda x: x[0])
        seq = np.stack([x[1] for x in feat_list], axis=0) # (T, 1280)
        sequences.append(seq)
        seq_labels.append(video_labels[vname])
        seq_names.append(vname)

    return np.array(sequences, dtype=np.float32), np.array(seq_labels, dtype=np.int64), seq_names


def train_temporal_model(train_seqs, train_lbls, val_seqs, val_lbls, epochs=15):
    print("\n=======================================================")
    print("PHASE 2: Training BiGRU Temporal Consistency Model")
    print("=======================================================")
    temporal_model = DeepGuardTemporalModel().to(DEVICE)
    # Class mapping: in DeepGuard class 0=Fake, 1=Real.
    # For temporal model: target 1=Synthetic (Fake), 0=Authentic (Real)
    # So temporal_target = 1 - label
    train_targets = 1 - train_lbls
    val_targets = 1 - val_lbls

    n_fake = np.sum(train_targets == 1)
    n_real = np.sum(train_targets == 0)
    pos_weight = float(n_real) / max(1, float(n_fake))
    criterion = nn.CrossEntropyLoss(weight=torch.tensor([1.0, pos_weight], device=DEVICE))
    optimizer = torch.optim.AdamW(temporal_model.parameters(), lr=1e-3, weight_decay=1e-3)

    X_tr = torch.from_numpy(train_seqs).to(DEVICE)
    y_tr = torch.from_numpy(train_targets).to(DEVICE)
    X_va = torch.from_numpy(val_seqs).to(DEVICE)
    y_va = torch.from_numpy(val_targets).to(DEVICE)

    best_val_acc = 0.0
    best_weights = copy.deepcopy(temporal_model.state_dict())

    for epoch in range(1, epochs + 1):
        temporal_model.train()
        optimizer.zero_grad()
        logits, _ = temporal_model(X_tr)
        loss = criterion(logits, y_tr)
        loss.backward()
        optimizer.step()

        preds = logits.argmax(dim=1)
        tr_acc = (preds == y_tr).float().mean().item()

        temporal_model.eval()
        with torch.no_grad():
            v_logits, _ = temporal_model(X_va)
            v_preds = v_logits.argmax(dim=1)
            va_acc = (v_preds == y_va).float().mean().item()

        if va_acc >= best_val_acc:
            best_val_acc = va_acc
            best_weights = copy.deepcopy(temporal_model.state_dict())

        if epoch % 5 == 0 or epoch == epochs:
            print(f"Epoch {epoch:02d}/{epochs} | Train Loss: {loss.item():.4f}, Acc: {tr_acc:.4f} | Val Acc: {va_acc:.4f}")

    temporal_model.load_state_dict(best_weights)
    out_path = Path("ai/models/deepguard_temporal_v5.pth")
    torch.save({
        "model_state_dict": temporal_model.state_dict(),
        "model_name": "DeepGuard-BiGRU-Temporal",
        "model_version": "5.0.0",
        "best_val_acc": best_val_acc
    }, out_path)
    print(f"--> Saved Temporal Model to {out_path} (Best Val Acc: {best_val_acc:.4f})")
    return temporal_model


def evaluate_frame_level(model, test_items, base_dir, transform):
    print("\n--> Evaluating Frame-Level Performance Independently (288 Test Frames)...")
    model.eval()
    dataset = FrameDataset(test_items, base_dir, transform=transform)
    loader = DataLoader(dataset, batch_size=32, shuffle=False)

    y_true = []
    y_pred = []
    y_scores = []

    with torch.no_grad():
        for imgs, labels, _, _ in loader:
            imgs = imgs.to(DEVICE)
            logits = model(imgs)
            probs = F.softmax(logits, dim=1)
            # Class 0=Fake, Class 1=Real. Target fake=1, real=0
            p_fake = probs[:, 0].cpu().numpy()
            preds = (p_fake >= 0.50).astype(int)
            targets = (labels.numpy() == 0).astype(int)

            y_true.extend(targets.tolist())
            y_pred.extend(preds.tolist())
            y_scores.extend(p_fake.tolist())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_scores = np.array(y_scores)

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_scores)),
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
        "total_frames": len(y_true)
    }
    return metrics


def evaluate_video_level(frame_model, temporal_model, test_seqs, test_lbls, test_names, test_items, base_dir, transform):
    print("\n--> Evaluating Video-Level Performance Independently (24 Test Videos)...")
    frame_model.eval()
    temporal_model.eval()

    # Precompute frame probabilities
    dataset = FrameDataset(test_items, base_dir, transform=transform)
    loader = DataLoader(dataset, batch_size=32, shuffle=False)
    frame_scores = defaultdict(list)

    with torch.no_grad():
        for imgs, _, vid_names, orders in loader:
            imgs = imgs.to(DEVICE)
            probs = F.softmax(frame_model(imgs), dim=1)
            p_fake = probs[:, 0].cpu().numpy()
            for p, vname, ord_idx in zip(p_fake, vid_names, orders.numpy()):
                frame_scores[vname].append((ord_idx, p))

    # Precompute temporal probabilities
    X_te = torch.from_numpy(test_seqs).to(DEVICE)
    with torch.no_grad():
        t_logits, attn_weights = temporal_model(X_te)
        t_probs = F.softmax(t_logits, dim=1)[:, 1].cpu().numpy() # Probability of synthetic

    y_true = []
    y_pred = []
    y_scores = []
    video_details = []

    for idx, (vname, t_score) in enumerate(zip(test_names, t_probs)):
        label = test_lbls[idx] # 1=Real, 0=Fake
        ground_truth_fake = 1 if label == 0 else 0

        # Sort frame scores
        f_list = sorted(frame_scores[vname], key=lambda x: x[0])
        f_vals = [x[1] for x in f_list]
        k = max(2, int(np.ceil(0.35 * len(f_vals))))
        top_k_mean = float(np.mean(sorted(f_vals, reverse=True)[:k]))
        overall_mean = float(np.mean(f_vals))
        face_composite = 0.70 * top_k_mean + 0.30 * overall_mean

        # Combine with temporal model
        composite = 0.70 * face_composite + 0.30 * float(t_score)
        n_suspicious = sum(1 for s in f_vals if s >= 0.45)

        # Multi-frame decision rule
        is_synthetic = (n_suspicious >= 2 or top_k_mean >= 0.40 or composite >= 0.45)
        pred_bin = 1 if is_synthetic else 0

        y_true.append(ground_truth_fake)
        y_pred.append(pred_bin)
        y_scores.append(composite)

        video_details.append({
            "video_name": vname,
            "ground_truth": "FAKE" if ground_truth_fake == 1 else "REAL",
            "prediction": "synthetic" if pred_bin == 1 else "authentic",
            "composite_score": round(composite, 4),
            "top_k_mean": round(top_k_mean, 4),
            "temporal_score": round(float(t_score), 4),
            "suspicious_frames_count": n_suspicious
        })

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_scores = np.array(y_scores)

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_scores)),
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
        "total_videos": len(y_true),
        "details": video_details
    }
    return metrics


def main():
    base_dir = Path("ai/datasets/video_benchmark")
    manifest_path = base_dir / "dataset_manifest.json"
    with open(manifest_path, "r") as f:
        manifest_data = json.load(f)

    frames = manifest_data["frames"]
    train_items = [f for f in frames if f["split"] == "train"]
    val_items = [f for f in frames if f["split"] == "val"]
    test_items = [f for f in frames if f["split"] == "test"]

    print(f"Loaded {len(frames)} total frames:")
    print(f"  Train: {len(train_items)} | Val: {len(val_items)} | Test: {len(test_items)}")

    # Class weighting for frame training
    n_real = sum(1 for f in train_items if f["class"] == 1)
    n_fake = sum(1 for f in train_items if f["class"] == 0)
    w_fake = 1.0
    w_real = float(n_fake) / max(1, float(n_real))
    class_weights = torch.tensor([w_fake, w_real], dtype=torch.float32)
    print(f"Train Real: {n_real}, Fake: {n_fake} | Weights: Real={w_real:.2f}, Fake={w_fake:.2f}")

    train_trans, eval_trans = get_transforms()
    train_loader = DataLoader(FrameDataset(train_items, base_dir, transform=train_trans), batch_size=32, shuffle=True)
    val_loader = DataLoader(FrameDataset(val_items, base_dir, transform=eval_trans), batch_size=32, shuffle=False)

    # 1. Train Frame Model
    frame_model = train_frame_model(train_loader, val_loader, class_weights, epochs=3)

    # 2. Extract Sequential Embeddings
    print("\n--> Extracting sequential embeddings for temporal consistency modeling...")
    tr_seqs, tr_lbls, tr_names = extract_video_sequences(frame_model, train_items, base_dir, eval_trans)
    va_seqs, va_lbls, va_names = extract_video_sequences(frame_model, val_items, base_dir, eval_trans)
    te_seqs, te_lbls, te_names = extract_video_sequences(frame_model, test_items, base_dir, eval_trans)

    # 3. Train Temporal Model
    temporal_model = train_temporal_model(tr_seqs, tr_lbls, va_seqs, va_lbls, epochs=15)

    # 4. Measure Frame-Level Performance Independently
    frame_metrics = evaluate_frame_level(frame_model, test_items, base_dir, eval_trans)

    # 5. Measure Video-Level Performance Independently
    video_metrics = evaluate_video_level(
        frame_model, temporal_model,
        te_seqs, te_lbls, te_names,
        test_items, base_dir, eval_trans
    )

    # Print Summary Comparison
    print("\n=======================================================")
    print("INDEPENDENT EVALUATION RESULTS ON HELD-OUT TEST DATA")
    print("=======================================================")
    print(f"FRAME-LEVEL (288 test frames from unseen identities):")
    print(f"  Accuracy:  {frame_metrics['accuracy']:.4f}")
    print(f"  Precision: {frame_metrics['precision']:.4f}")
    print(f"  Recall:    {frame_metrics['recall']:.4f}")
    print(f"  F1-Score:  {frame_metrics['f1']:.4f}")
    print(f"  ROC-AUC:   {frame_metrics['roc_auc']:.4f}")
    print(f"  Confusion: TP={frame_metrics['tp']}, TN={frame_metrics['tn']}, FP={frame_metrics['fp']}, FN={frame_metrics['fn']}")

    print(f"\nVIDEO-LEVEL (24 test videos from unseen identities):")
    print(f"  Accuracy:  {video_metrics['accuracy']:.4f}")
    print(f"  Precision: {video_metrics['precision']:.4f}")
    print(f"  Recall:    {video_metrics['recall']:.4f}")
    print(f"  F1-Score:  {video_metrics['f1']:.4f}")
    print(f"  ROC-AUC:   {video_metrics['roc_auc']:.4f}")
    print(f"  Confusion: TP={video_metrics['tp']}, TN={video_metrics['tn']}, FP={video_metrics['fp']}, FN={video_metrics['fn']}")

    # Save results
    results_path = base_dir / "evaluation_results_v5.json"
    with open(results_path, "w") as f:
        json.dump({
            "frame_level": frame_metrics,
            "video_level": video_metrics
        }, f, indent=2)
    print(f"\nSaved detailed evaluation metrics to {results_path}")

if __name__ == "__main__":
    main()
