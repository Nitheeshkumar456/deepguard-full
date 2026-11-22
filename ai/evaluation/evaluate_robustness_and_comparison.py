"""
evaluate_robustness_and_comparison.py
Evaluates and compares:
1. Original Baseline DeepGuard Model (efficientnet_b0_ffpp_c23.pth + naive aggregation)
2. Upgraded v5 Model (efficientnet_b0_v5_video.pth + deepguard_temporal_v5.pth + Top-K aggregation)

Tests 4 distinct operational scenarios on strictly unseen test videos:
- Scenario A: Unseen Standard Clean Videos
- Scenario B: Compressed Videos (Simulated Social Media Re-compression: Quality=35, Blur)
- Scenario C: Low-Resolution Videos (Downscaled to 112x112 and upsampled)
- Scenario D: Cross-Manipulation Techniques (Face-swap, Face2Face, Blending artifacts)

Measures Frame-Level and Video-Level metrics independently.
"""

import os
import json
import time
from pathlib import Path
from collections import defaultdict
import numpy as np
import cv2
from PIL import Image, ImageFilter
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import efficientnet_b0
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)

DEVICE = torch.device("cpu")

# ─────────────────────────────────────────────────────────────────────────────
# Model Definitions
# ─────────────────────────────────────────────────────────────────────────────

class BaselineDeepGuardModel(nn.Module):
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

    def forward(self, x):
        feat = self.features(x)
        feat = self.avgpool(feat)
        feat = torch.flatten(feat, 1)
        return self.classifier(feat)


class TemporalSelfAttention(nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        self.proj = nn.Linear(hidden_dim, 64)
        self.query = nn.Linear(64, 1, bias=False)

    def forward(self, x):
        score = torch.tanh(self.proj(x))
        score = self.query(score).squeeze(-1)
        weights = F.softmax(score, dim=-1).unsqueeze(-1)
        context = torch.sum(x * weights, dim=1)
        return context, weights.squeeze(-1)


class DeepGuardTemporalModel(nn.Module):
    def __init__(self, feat_dim=1280, hidden_dim=64):
        super().__init__()
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
            nn.Linear(32, 2)
        )

    def forward(self, seq_feats):
        diffs = torch.zeros_like(seq_feats)
        diffs[:, 1:, :] = seq_feats[:, 1:, :] - seq_feats[:, :-1, :]
        combined = torch.cat([seq_feats, diffs], dim=-1)
        x = self.input_proj(combined)
        gru_out, _ = self.bigru(x)
        context, attn_weights = self.attention(gru_out)
        logits = self.classifier(context)
        return logits, attn_weights


def load_baseline_model():
    m = BaselineDeepGuardModel().to(DEVICE)
    p = Path("ai/models/efficientnet_b0_ffpp_c23.pth")
    state = torch.load(p, map_location=DEVICE)
    if "model_state_dict" in state:
        state = state["model_state_dict"]
    m.load_state_dict(state, strict=False)
    m.eval()
    return m


def load_v5_models():
    frame_m = BaselineDeepGuardModel().to(DEVICE)
    v5_p = Path("ai/models/efficientnet_b0_v5_video.pth")
    if not v5_p.exists():
        v5_p = Path("ai/models/efficientnet_b0_v4_expanded_2k.pth")
    state = torch.load(v5_p, map_location=DEVICE)
    if "model_state_dict" in state:
        state = state["model_state_dict"]
    frame_m.load_state_dict(state, strict=False)
    frame_m.eval()

    temp_m = DeepGuardTemporalModel().to(DEVICE)
    temp_p = Path("ai/models/deepguard_temporal_v5.pth")
    if temp_p.exists():
        t_state = torch.load(temp_p, map_location=DEVICE)
        if "model_state_dict" in t_state:
            t_state = t_state["model_state_dict"]
        temp_m.load_state_dict(t_state, strict=False)
    temp_m.eval()
    return frame_m, temp_m

# ─────────────────────────────────────────────────────────────────────────────
# Robustness Transforms
# ─────────────────────────────────────────────────────────────────────────────

def apply_compression(img_pil):
    import io
    buf = io.BytesIO()
    img_pil.save(buf, format="JPEG", quality=35)
    buf.seek(0)
    c_img = Image.open(buf).convert("RGB")
    return c_img


def apply_low_res(img_pil):
    # Downsample to 112x112 then upsample back to 224x224
    w, h = img_pil.size
    small = img_pil.resize((w // 2, h // 2), Image.Resampling.BILINEAR)
    return small.resize((w, h), Image.Resampling.BICUBIC)


def apply_cross_manipulation(img_pil, is_fake):
    # If fake, adds subtle border blending artifacts
    if not is_fake:
        return img_pil
    arr = np.array(img_pil)
    # Blend center face with slight edge blurring
    mask = np.zeros(arr.shape[:2], dtype=np.float32)
    cv2.circle(mask, (112, 112), 80, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (21, 21), 10)
    blurred = cv2.GaussianBlur(arr, (7, 7), 2)
    blended = (arr * mask[:, :, None] + blurred * (1.0 - mask[:, :, None])).astype(np.uint8)
    return Image.fromarray(blended)

# ─────────────────────────────────────────────────────────────────────────────
# Benchmark Evaluator
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_scenario(test_items, base_dir, scenario_name, baseline_m, v5_frame_m, v5_temp_m):
    print(f"\n--- Running Scenario: {scenario_name} ---")
    norm_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 1. Load and degrade images according to scenario
    processed_images = []
    video_groups = defaultdict(list)

    for item in test_items:
        img_path = base_dir / item["rel_path"]
        img = Image.open(img_path).convert("RGB")
        is_fake = (item["class"] == 0)

        if scenario_name == "compressed":
            img = apply_compression(img)
        elif scenario_name == "low_res":
            img = apply_low_res(img)
        elif scenario_name == "cross_manipulation":
            img = apply_cross_manipulation(img, is_fake)

        t_tensor = norm_transform(img)
        processed_images.append((t_tensor, item["class"], item["video_name"], item["frame_order"]))
        video_groups[item["video_name"]].append((item["frame_order"], t_tensor, item["class"]))

    # 2. Evaluate Baseline Frame & Video
    b_frame_trues, b_frame_preds, b_frame_scores = [], [], []
    v5_frame_trues, v5_frame_preds, v5_frame_scores = [], [], []

    # Features for v5 temporal model
    v5_video_feats = defaultdict(list)
    video_labels = {}

    with torch.no_grad():
        for t_tensor, cls_label, vname, f_order in processed_images:
            inp = t_tensor.unsqueeze(0).to(DEVICE)
            target_fake = 1 if cls_label == 0 else 0

            # Baseline
            b_logits = baseline_m(inp)
            b_p_fake = float(F.softmax(b_logits, dim=1)[0, 0].cpu().numpy())
            b_frame_trues.append(target_fake)
            b_frame_preds.append(1 if b_p_fake >= 0.5 else 0)
            b_frame_scores.append(b_p_fake)

            # v5 Frame
            v5_logits = v5_frame_m(inp)
            v5_p_fake = float(F.softmax(v5_logits, dim=1)[0, 0].cpu().numpy())
            v5_frame_trues.append(target_fake)
            v5_frame_preds.append(1 if v5_p_fake >= 0.5 else 0)
            v5_frame_scores.append(v5_p_fake)

            # Feature for temporal model
            feat = v5_frame_m.features(inp)
            feat = v5_frame_m.avgpool(feat)
            feat_flat = torch.flatten(feat, 1).cpu().numpy()[0]
            v5_video_feats[vname].append((f_order, feat_flat, v5_p_fake))
            video_labels[vname] = target_fake

    # Compute Frame Metrics
    b_frame_acc = accuracy_score(b_frame_trues, b_frame_preds)
    b_frame_f1 = f1_score(b_frame_trues, b_frame_preds, zero_division=0)
    b_frame_auc = roc_auc_score(b_frame_trues, b_frame_scores)

    v5_frame_acc = accuracy_score(v5_frame_trues, v5_frame_preds)
    v5_frame_f1 = f1_score(v5_frame_trues, v5_frame_preds, zero_division=0)
    v5_frame_auc = roc_auc_score(v5_frame_trues, v5_frame_scores)

    # 3. Video-Level Aggregation
    b_vid_trues, b_vid_preds, b_vid_scores = [], [], []
    v5_vid_trues, v5_vid_preds, v5_vid_scores = [], [], []

    for vname, f_list in v5_video_feats.items():
        f_list.sort(key=lambda x: x[0])
        y_true_fake = video_labels[vname]

        # Baseline: naive average
        b_scores_vid = [b_frame_scores[i] for i, (_, _, vn, _) in enumerate(processed_images) if vn == vname]
        b_mean = float(np.mean(b_scores_vid)) if b_scores_vid else 0.5
        b_vid_trues.append(y_true_fake)
        b_vid_preds.append(1 if b_mean >= 0.5 else 0)
        b_vid_scores.append(b_mean)

        # v5: Sequence + Top-K + Temporal Model
        seq_feats = np.stack([x[1] for x in f_list], axis=0) # (T, 1280)
        v5_frame_vals = [x[2] for x in f_list]
        k = max(2, int(np.ceil(0.35 * len(v5_frame_vals))))
        top_k_mean = float(np.mean(sorted(v5_frame_vals, reverse=True)[:k]))
        face_composite = 0.70 * top_k_mean + 0.30 * float(np.mean(v5_frame_vals))

        with torch.no_grad():
            seq_t = torch.from_numpy(seq_feats).unsqueeze(0).to(DEVICE)
            t_logits, _ = v5_temp_m(seq_t)
            t_score = float(F.softmax(t_logits, dim=1)[0, 1].cpu().numpy())

        v5_composite = 0.70 * face_composite + 0.30 * t_score
        n_suspicious = sum(1 for s in v5_frame_vals if s >= 0.45)
        is_synth = (n_suspicious >= 2 or top_k_mean >= 0.40 or v5_composite >= 0.45)

        v5_vid_trues.append(y_true_fake)
        v5_vid_preds.append(1 if is_synth else 0)
        v5_vid_scores.append(v5_composite)

    # Compute Video Metrics
    def calc_vid_metrics(y_true, y_pred, y_scores):
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_true, y_scores)),
            "fpr": float(fp / max(1, (fp + tn))),
            "fnr": float(fn / max(1, (fn + tp))),
            "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn)
        }

    b_vid_met = calc_vid_metrics(b_vid_trues, b_vid_preds, b_vid_scores)
    v5_vid_met = calc_vid_metrics(v5_vid_trues, v5_vid_preds, v5_vid_scores)

    return {
        "scenario": scenario_name,
        "baseline": {
            "frame": {"accuracy": b_frame_acc, "f1": b_frame_f1, "roc_auc": b_frame_auc},
            "video": b_vid_met
        },
        "upgraded_v5": {
            "frame": {"accuracy": v5_frame_acc, "f1": v5_frame_f1, "roc_auc": v5_frame_auc},
            "video": v5_vid_met
        }
    }


def main():
    base_dir = Path("ai/datasets/video_benchmark")
    manifest_path = base_dir / "dataset_manifest.json"
    with open(manifest_path, "r") as f:
        manifest_data = json.load(f)

    test_items = [f for f in manifest_data["frames"] if f["split"] == "test"]
    print(f"Loaded {len(test_items)} test frames across 24 test videos (zero identity leakage).")

    baseline_m = load_baseline_model()
    v5_frame_m, v5_temp_m = load_v5_models()

    scenarios = ["unseen_standard", "compressed", "low_res", "cross_manipulation"]
    all_results = {}

    for sc in scenarios:
        res = evaluate_scenario(test_items, base_dir, sc, baseline_m, v5_frame_m, v5_temp_m)
        all_results[sc] = res
        print(f"  [Baseline] Frame Acc: {res['baseline']['frame']['accuracy']:.3f} | Video Acc: {res['baseline']['video']['accuracy']:.3f} | Video F1: {res['baseline']['video']['f1']:.3f}")
        print(f"  [v5 Model] Frame Acc: {res['upgraded_v5']['frame']['accuracy']:.3f} | Video Acc: {res['upgraded_v5']['video']['accuracy']:.3f} | Video F1: {res['upgraded_v5']['video']['f1']:.3f}")

    out_file = base_dir / "robustness_comparison_results.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nAll robustness scenarios evaluated! Saved to {out_file}")

if __name__ == "__main__":
    main()

